# -*- coding: utf-8 -*-
import re
import requests
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import logout
from django.contrib.auth.models import AbstractUser
from bs4 import BeautifulSoup


def pretty_join(items, word='and'):
    new_list = items[:-2]
    new_list.append((" %s " % word).join(items[-2:]))
    return u', '.join(new_list)


def get_soup(url):
    request = requests.get(url, cookies={'bb_userid': str(settings.SEREBII_USER_ID), 'bb_password': settings.SEREBII_USER_PWHASH})
    return BeautifulSoup(request.text, 'html.parser')


def get_post_author(post):
    user_link = post.find('div', class_="username_container").find('a', class_="username")
    username = user_link.strong.get_text(strip=True)
    user_id = MemberPage.get_params_from_url(user_link['href'])['user_id']
    return Member(user_id=user_id, username=username)


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
        if not force_download:
            return cls(cls.object_class.from_params(**params))
        soup = get_soup(url)
        obj = cls.object_from_soup(soup, **params)
        return cls(obj, soup)

    @classmethod
    def object_from_soup(cls, soup, **kwargs):
        """
        Returns an object corresponding to the given soup.

        """
        return cls.object_class.from_soup(soup, **kwargs)

    @classmethod
    def get_params_from_url(cls, url):
        """
        Extracts relevant parameters from a Serebii URL.

        """
        url_regex = re.compile(r'^(?:http:\/\/(?:www\.)?serebiiforums\.com\/)?%s\.php\?(%s)' % (cls.page, cls.object_id_regex), re.U)
        match = url_regex.match(url)
        if match is None or not match.group(1): # The URL is invalid if the object ID match is zero-length
            raise ValueError(u"Invalid %s URL." % cls.__name__)
        else:
            return match.groupdict()

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
        if self._soup is not None:
            return self._soup
        else:
            return get_soup(self.get_url())


class SerebiiObject(object):
    """
    A base class mixin for Serebii objects.

    """
    @classmethod
    def from_soup(cls, soup, **kwargs):
        """
        Returns an object corresponding to the given soup.

        """
        return cls(**kwargs)

    @classmethod
    def from_params(cls, save=False, **kwargs):
        """
        Returns an object corresponding to the given params.

        """
        try:
            # See if we can get the object from the database just from the parameters
            return cls.objects.get(**kwargs)
        except (cls.DoesNotExist, cls.MultipleObjectsReturned):
            # Either this doesn't exist in the database or we can't uniquely determine the
            # object from the URL parameters, so fetch it from the forums instead.
            obj = cls.from_soup(get_soup(cls(**kwargs).link()), **kwargs)
            if save:
                obj.save()
            return obj

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
        page_class = self.__class__.get_page_class()
        return page_class(self)


class MemberManager(models.Manager):
    def nominated_in_year(self, year):
        return self.get_queryset().filter(Q(nominations__year=year) | Q(fics__nominations__year=year)).distinct()


class Member(SerebiiObject, models.Model):
    user_id = models.PositiveIntegerField(unique=True, primary_key=True)
    username = models.CharField(max_length=50)

    objects = MemberManager()

    class Meta:
        ordering = ['username']

    def __unicode__(self):
        return self.username

    def to_dict(self):
        return {'type': 'nominee', 'pk': self.pk, 'name': unicode(self), 'object': {'username': self.username}}

    def link(self):
        return u"http://www.serebiiforums.com/member.php?%s" % self.user_id

    def link_html(self):
        return u'<a href="%s">%s</a>' % (self.link(), self.username)

    def link_bbcode(self):
        return u'[url=%s]%s[/url]' % (self.link(), self.username)

    @classmethod
    def get_page_class(self):
        return MemberPage

    def save(self, *args, **kwargs):
        self.user_id = int(self.user_id)
        return super(Member, self).save(*args, **kwargs)

    @classmethod
    def from_soup(cls, soup, user_id):
        username = soup.find('span', class_=u"member_username").text
        return cls(user_id=user_id, username=username)


class MemberPage(SerebiiPage):
    page = 'member'
    object_id_regex = r'(?:u=)?(?P<user_id>\d+)'
    object_class = Member


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


class FicManager(models.Manager):
    def get_queryset(self):
        return super(FicManager, self).get_queryset().prefetch_related('authors')

    def nominated_in_year(self, year):
        return self.get_queryset().filter(nominations__year=year).distinct()


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

    def link(self):
        if self.post_id:
            urlbit = u"p=%(post)s#post%(post)s" % {'post': self.post_id}
        else:
            urlbit = "t=%s" % self.thread_id
        return u"http://www.serebiiforums.com/showthread.php?%s" % urlbit

    def link_html(self):
        return u'<a href="%s">%s</a> by %s' % (self.link(), self.title, pretty_join([author.link_html() for author in self.authors.all()]))

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

    @classmethod
    def from_soup(cls, soup, thread_id, post_id):
        if thread_id is None and post_id is None:
            raise ValidationError(u"You chose to nominate the thread, but you've entered a link to a post with no thread ID. Please enter a thread link.")

        forum_link = soup.find(id="breadcrumb").find_all('li', class_="navbit")[-2].a
        if forum_link['href'] not in (u'forumdisplay.php?32-Fan-Fiction', u'forumdisplay.php?33-Non-Pokémon-Stories', u'forumdisplay.php?110-Completed-Fics'):
            raise ValidationError(u"This thread does not seem to be a fanfic (it is not located in the Fan Fiction, Non-Pokémon Stories or Completed Fics forums). Please enter the link to a valid fanfic.")

        title_link = soup.find('span', class_="threadtitle").a

        if post_id is not None:
            # The fic starts in a particular post - use the author of the post and a placeholder title
            post = soup.find(id="post_%s" % post_id)
            title = "%s - post %s" % (title_link.get_text(strip=True), post_id)
            author = get_post_author(post)
        else:
            # The fic is a thread - use the thread title and the author of the first post
            title = title_link.get_text(strip=True)
            author = get_post_author(soup.find(id="posts").li)

        if thread_id is None:
            thread_id = FicPage.get_params_from_url(title_link['href'])['thread_id']

        obj = cls(title=title, thread_id=thread_id, post_id=post_id)
        obj._authors = [author]
        return obj


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
