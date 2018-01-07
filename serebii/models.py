# -*- coding: utf-8 -*-
import re
import requests
from datetime import datetime, timedelta
from dateutil import parser, tz
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import logout
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from bs4 import BeautifulSoup


def get_tz_string(offset):
    return '{:0=+3d}00'.format(offset)


def pretty_join(items, word='and'):
    new_list = items[:-2]
    new_list.append((" %s " % word).join(items[-2:]))
    return u', '.join(new_list)


def get_soup(url):
    request = requests.get(url, cookies={'bb_userid': str(settings.SEREBII_USER_ID), 'bb_password': settings.SEREBII_USER_PWHASH})
    return BeautifulSoup(request.text, 'html.parser')


class SerebiiPage(object):
    """
    A base class for a Serebii page. MemberPage and FicPage inherit
    from this to work with fic threads/profiles.

    """
    page = None
    object_id_regex = r''
    object_class = None

    def __init__(self, obj, soup=None):
        self.object = obj
        self._soup = soup
        self._time_info = None

    def __unicode__(self):
        return u"Serebii page for %s" % self.object

    def __str__(self):
        return unicode(self).encode('utf-8')

    @classmethod
    def from_url(cls, url, force_download=False):
        """
        Takes a URL to a Serebii page for this object type and returns
        a corresponding page instance.

        If force_download is True, the page will always be fetched and
        parsed; otherwise, it'll just grab the relevant parameters from
        the URL and find an existing object matching those parameters,
        if one exists.

        """
        params = cls.get_params_from_url(url)  # Will raise ValueError if the URL is invalid
        return cls.from_params(force_download=force_download, url=url, **params)

    @classmethod
    def from_params(cls, save=False, force_download=False, url=None, **kwargs):
        """
        Returns a page object corresponding to the given params.

        """
        if not force_download:
            try:
                # See if we can get the object from the database just from the
                # parameters
                obj = cls.object_class.objects.get(**kwargs)
                return cls(obj)
            except (cls.object_class.DoesNotExist, cls.object_class.MultipleObjectsReturned):
                pass
        # Either this doesn't exist in the database, we can't uniquely
        # determine the object from the URL parameters, or we simply need to
        # refetch it for validation purposes, so fetch it from the forums
        obj = cls.object_class(**kwargs)
        page = cls(obj, get_soup(url) if url else None)
        page.load_object(save)
        return page

    @classmethod
    def get_params_from_url(cls, url):
        """
        Extracts relevant parameters from a Serebii URL.

        """
        url_regex = re.compile(r'^(?:https?:\/\/(?:www\.)?serebiiforums\.com\/)?%s\.php\?(%s)' % (cls.page, cls.object_id_regex), re.U)
        match = url_regex.match(url)
        if match is None or not match.group(1):  # The URL is invalid if the object ID match is zero-length
            raise ValueError(u"Invalid %s URL." % cls.__name__)
        else:
            return match.groupdict()

    def load_object(self, save=True):
        """
        Fetches the page from the forums and populates self.object with it.

        """
        pass

    def get_url(self):
        """
        Returns a URL for this page.

        """
        return self.object.link()

    def get_soup(self):
        """
        Returns a soup for this page. If we don't have a cached one,
        we'll fetch the page first.

        """
        if self._soup is None:
            self._soup = get_soup(self.get_url())
        return self._soup

    def get_time_info(self):
        """
        Returns the forum's current date and timezone offset. This is
        cached.

        """
        if not self._time_info:
            time_text = self.get_soup().find('div', id="footer_time").get_text()
            sentences = time_text.split('.')

            tz_sentence = sentences[0]
            offset = tz_sentence.split(' ')[-1]
            offset = 0 if offset == 'GMT' else int(offset)

            time_sentence = sentences[1]
            time = ' '.join(time_sentence.split(' ')[-2:])

            self._time_info = (parser.parse(time), offset)
        return self._time_info


class SerebiiObject(object):
    """
    A base class mixin for Serebii objects.

    """
    _page = None

    @classmethod
    def get_page_class(self):
        """
        Returns the page class for this object type.

        """
        return SerebiiPage

    def get_page(self):
        """
        Returns a SerebiiPage instance corresponding to this object.

        """
        if self._page:
            return self._page
        page_class = self.__class__.get_page_class()
        return page_class(self)


class MemberQuerySet(models.QuerySet):
    def nominated_in_year(self, year):
        return self.filter(Q(nominations__year=year) | Q(fics__nominations__year=year)).distinct()

    def guests(self):
        return self.filter(user_id__gte=1000000)

    def get_next_guest_id(self):
        latest_guest = self.guests().order_by('-user_id').first()
        return latest_guest.user_id + 1 if latest_guest else 1000000


class Member(SerebiiObject, models.Model):
    user_id = models.PositiveIntegerField(unique=True, primary_key=True)
    username = models.CharField(max_length=50)

    objects = MemberQuerySet.as_manager()

    class Meta:
        ordering = ['username']

    def __unicode__(self):
        return self.username

    def to_dict(self):
        return {'type': 'nominee', 'pk': self.pk, 'name': unicode(self), 'object': {'username': self.username}}

    def link(self):
        return u"http://www.serebiiforums.com/member.php?%s" % self.user_id

    def link_html(self):
        return u'<a href="%s" target="_blank">%s</a>' % (self.link(), self.username) if not self.is_guest() else self.username

    def link_bbcode(self):
        return u'[url=%s]%s[/url]' % (self.link(), self.username) if not self.is_guest() else self.username

    def is_guest(self):
        return self.user_id >= 1000000

    @classmethod
    def get_page_class(self):
        return MemberPage

    def save(self, *args, **kwargs):
        if self.user_id is None:
            # Check if we already have a guest user with this username
            existing_guest = Member.objects.guests().filter(username=self.username).first()
            if existing_guest:
                self.user_id = existing_guest.user_id
            else:
                self.user_id = Member.objects.get_next_guest_id()
        self.user_id = int(self.user_id)
        return super(Member, self).save(*args, **kwargs)


class MemberPage(SerebiiPage):
    page = 'member'
    object_id_regex = r'(?:u=)?(?P<user_id>\d+)'
    object_class = Member

    def load_object(self, save=True):
        soup = self.get_soup()
        username = soup.find('span', class_=u"member_username").text
        self.object.username = username
        self.object._page = self
        if save:
            self.object.save()
        return self.object


def get_verification_code():
    return User.objects.make_random_password()


class User(AbstractUser):
    """
    A user object, not to be confused with a Serebii member.

    In order to do much of anything, users need to associate their
    account with a Serebii member (the member field). This is done
    either by verifying ownership of a Serebii account (in which case
    verified is True) or by registering a temporary account as that
    member (in which case verified is False, until the user is manually
    verified by an admin).

    """
    member = models.ForeignKey(Member, blank=True, null=True)
    verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=10, default=get_verification_code)


class UnverifiedUserMiddleware(object):
    """
    Check if the current user is an unverified temp user and if there
    is a verified user for the same member. If so, log the user out.

    This prevents unverified users from sneaking in to override a
    verified user's votes.

    """
    def process_request(self, request):
        if (
            request.user.is_authenticated() and
            request.user.member and
            not request.user.verified and
            User.objects.filter(member=request.user.member, verified=True).exists()
        ):
            logout(request)


class FicQuerySet(models.QuerySet):
    def nominated_in_year(self, year):
        return self.filter(nominations__year=year).distinct()


class FicManager(models.Manager):
    def get_queryset(self):
        return FicQuerySet(self.model, using=self._db).prefetch_related('authors')

    def nominated_in_year(self, year):
        return self.get_queryset().nominated_in_year(year)


class Fic(SerebiiObject, models.Model):
    """
    A fic, defined by its Serebii thread and possibly post ID.

    Right now, all fics are threads. Automating the detection of
    individual posts constituting separate fics is a hard problem.
    Maybe I will be motivated to figure it out if some multi-fic
    threads actually get nominated.

    """
    title = models.CharField(max_length=255)
    authors = models.ManyToManyField(Member, related_name='fics')
    thread_id = models.PositiveIntegerField()
    post_id = models.PositiveIntegerField(blank=True, null=True)
    posted_date = models.DateTimeField()

    objects = FicManager()

    _authors = []

    class Meta:
        unique_together = ['thread_id', 'post_id']
        ordering = ['title', 'thread_id', 'post_id']

    def __unicode__(self):
        if self.pk is not None:
            authors = [author.username for author in self.authors.all()]
        else:
            authors = [author.username for author in self._authors]
        return u"%s by %s" % (self.title, pretty_join(authors))

    def to_dict(self):
        return {'type': 'fic', 'pk': self.pk, 'name': unicode(self), 'object': {'title': self.title, 'authors': [author.pk for author in self.authors.all()]}}

    def get_authors(self):
        return list(self.authors.all()) if self.pk else self._authors

    def link(self):
        if self.post_id:
            urlbit = u"p=%(post)s#post%(post)s" % {'post': self.post_id}
        else:
            urlbit = "t=%s" % self.thread_id
        return u"http://www.serebiiforums.com/showthread.php?%s" % urlbit

    def link_html(self):
        return u'<a href="%s" target="_blank">%s</a> by %s' % (self.link(), self.title, pretty_join([author.link_html() for author in self.authors.all()]))

    def link_bbcode(self):
        return u'[%(type)s=%(id)s]%(title)s[/%(type)s] by %(authors)s' % {'type': 'post' if self.post_id else 'thread', 'id': self.post_id or self.thread_id, 'title': self.title, 'authors': pretty_join([author.link_bbcode() for author in self.authors.all()])}

    @classmethod
    def get_page_class(self):
        return FicPage

    def save(self, *args, **kwargs):
        if self.pk is None:
            # Check if a fic with this thread and post ID already exists
            try:
                existing_fic = Fic.objects.get(thread_id=self.thread_id, post_id=self.post_id)
                self.pk = existing_fic.pk
            except Fic.DoesNotExist:
                pass
        super(Fic, self).save(*args, **kwargs)
        if self._authors:
            for author in self._authors:
                author.save()
            existing_authors = self.authors.all()
            self.authors.add(*[author for author in self._authors if author not in existing_authors])


class FicPage(SerebiiPage):
    page = 'showthread'
    # This really gnarly regex matches URL queries for threads/posts including
    # - t=<threadid>
    # - t=<threadid>&p=<postid>
    # - p=<postid>
    # - <threadid>
    # - <threadid>&p=<postid>
    # - <threadid>-Fic-title
    # - <threadid>-Fic-title&p=<postid>
    # ...which should cover every sensible URL a person could enter for a
    # Serebii thread/post. It will technically also match an empty query
    # string, but we can handle that case separately.
    object_id_regex = r'(?:(?:t=)?(?P<thread_id>\d+)[^&]*)?(?:(?(thread_id)&)p=(?P<post_id>\d+))?'
    object_class = Fic

    _pagination = None

    def get_pagination(self):
        if not self._pagination:
            soup = self.get_soup()
            self._pagination = soup.find('div', id='pagination_top')
        return self._pagination

    def get_last_page(self):
        soup = self.get_soup()
        lastimg = soup.find('img', alt='Last')

        if lastimg:
            return FicPage.from_url(u"http://www.serebiiforums.com/{}".format(lastimg.parent['href']), force_download=True)
        else:
            return self

    def has_pages(self):
        pagination = self.get_pagination()
        page_span = pagination.find('span', class_="selected")
        return bool(page_span)

    def has_next_page(self):
        pagination = self.get_pagination()
        nextlink = pagination.find('a', rel='next')
        return bool(nextlink)

    def has_prev_page(self):
        pagination = self.get_pagination()
        prevlink = pagination.find('a', rel='prev')
        return bool(prevlink)

    def get_page_number(self):
        pagination = self.get_pagination()
        page_span = pagination.find('span', class_="selected")
        if page_span:
            return int(page_span.get_text(strip=True))
        else:
            return 1

    def get_next_page(self):
        pagination = self.get_pagination()
        nextlink = pagination.find('a', rel='next')
        if nextlink:
            return FicPage.from_url(u"http://www.serebiiforums.com/{}".format(nextlink['href']), force_download=True)
        else:
            return None

    def get_prev_page(self):
        pagination = self.get_pagination()
        prevlink = pagination.find('a', rel='prev')
        if prevlink:
            return FicPage.from_url(u"http://www.serebiiforums.com/{}".format(prevlink['href']), force_download=True)
        else:
            return None

    def get_post(self):
        if self.object.post_id:
            return Post(self, self.get_soup().find(id="post_%s" % self.object.post_id))
        else:
            return Post(self, self.get_soup().find(id="posts").li)

    def get_page_posts(self):
        soup = self.get_soup()
        return [Post(self, post) for post in soup.find(id="posts").find_all('li', recursive=False)]

    def is_fic(self):
        forum_link = self.get_soup().find(id="breadcrumb").find_all('li', class_="navbit")[-2].a
        return forum_link['href'] in (u'forumdisplay.php?32-Fan-Fiction', u'forumdisplay.php?33-Non-Pokémon-Stories', u'forumdisplay.php?110-Completed-Fics')

    def load_object(self, save=True):
        if self.object.thread_id is None and self.object.post_id is None:
            raise ValidationError(u"No parameters given")

        soup = self.get_soup()

        if not self.is_fic():
            raise ValidationError(u"This thread does not seem to be a fanfic (it is not located in the Fan Fiction, Non-Pokémon Stories or Completed Fics forums). Please enter the link to a valid fanfic.")

        title_link = soup.find('span', class_="threadtitle").a

        if self.object.thread_id is None:
            self.object.thread_id = FicPage.get_params_from_url(title_link['href'])['thread_id']

        post = self.get_post()

        if self.object.post_id is not None:
            # The fic starts in a particular post - use the author of the post and a placeholder title
            title = "%s - post %s" % (title_link.get_text(strip=True), self.object.post_id)
        else:
            # The fic is a thread - use the thread title and the author of the first post
            title = title_link.get_text(strip=True)

        self.object.title = title
        self.object.posted_date = post.posted_date
        self.object._authors = [post.author]
        self.object._page = self
        if save:
            self.object.save()
        return self.object


class Post(object):
    def __init__(self, page, post_soup):
        self.page = page
        self._soup = post_soup

    def __unicode__(self):
        return u'Post #{} by {} in {} (posted {})'.format(self.post_id, self.author, self.page.object, self.posted_date)

    def __repr__(self):
        return u'<{}>'.format(self)

    @property
    def post_id(self):
        return int(self._soup['id'][5:])

    @property
    def posted_date(self):
        forum_time, tz_offset = self.page.get_time_info()
        postdate = self._soup.find('span', class_="date").get_text(strip=True)

        tz_string = get_tz_string(tz_offset)

        now = timezone.now().astimezone(tz.tzoffset(None, tz_offset * 60 * 60))
        if forum_time.hour == 23 and now.hour == 0:
            # The forum time is actually still on the previous day
            forum_today = now.date() - timedelta(days=1)
        elif forum_time.hour == 0 and now.hour == 23:
            # The forum time is on the next day
            forum_today = now.date() + timedelta(days=1)
        else:
            forum_today = now.date()

        if 'Yesterday' in postdate:
            yesterday = forum_today - timedelta(days=1)
            datebit = yesterday.strftime('%d/%m/%Y')
            postdate = '{} {}'.format(datebit, postdate[postdate.rfind(',') + 1:])
        if 'Today' in postdate:
            datebit = forum_today.strftime('%d/%m/%Y')
            postdate = '{} {}'.format(datebit, postdate[postdate.rfind(',') + 1:])

        return parser.parse('{} {}'.format(postdate, tz_string)).astimezone(timezone.utc)

    @property
    def author(self):
        user_elem = self._soup.find(class_="username")
        if user_elem.name == 'a':
            # It's a registered user's linked username
            username = user_elem.strong.get_text(strip=True)
            try:
                user_id = int(MemberPage.get_params_from_url(user_elem['href'])['user_id'])
            except ValueError:
                # It's a deleted post and we can't get a proper URL - let's make it a guest.
                user_id = None
        else:
            # It's (presumably) a guest
            username = user_elem.get_text(strip=True)
            user_id = None
        return Member(user_id=user_id, username=username)
