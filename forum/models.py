# -*- coding: utf-8 -*-
import re
import requests
from datetime import datetime
from dateutil import parser
from pytz import timezone, utc
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import logout
from django.contrib.auth.models import AbstractUser
from bs4 import BeautifulSoup


def get_tz_string(offset):
    return '{:0=+3d}00'.format(offset)


def pretty_join(items, word='and'):
    new_list = items[:-2]
    new_list.append((" %s " % word).join(items[-2:]))
    return u', '.join(new_list)


def get_soup(url):
    request = requests.get(url)
    return BeautifulSoup(request.text, 'html.parser')


class ForumPage(object):
    """
    A base class for a forum page. MemberPage and FicPage inherit
    from this to work with fic threads/profiles.

    """
    object_id_regexen = []
    object_class = None

    def __init__(self, obj, soup=None):
        self.object = obj
        self._soup = soup
        self._time_info = None

    def __str__(self):
        return u"Forum page for %s" % self.object

    @classmethod
    def from_url(cls, url, force_download=False, save=False):
        """
        Takes a URL to a forum page for this object type and returns
        a corresponding page instance.

        If force_download is True, the page will always be fetched and
        parsed; otherwise, it'll just grab the relevant parameters from
        the URL and find an existing object matching those parameters,
        if one exists.

        """
        params = cls.get_params_from_url(url)  # Will raise ValueError if the URL is invalid
        return cls.from_params(force_download=force_download, url=url, save=save, **params)

    @classmethod
    def from_params(cls, save=False, force_download=False, url=None, object_type=None, **kwargs):
        """
        Returns a page object corresponding to the given params.

        """
        lookup_kwargs = dict(**kwargs)
        if 'post_id' in lookup_kwargs and object_type != 'post':
            lookup_kwargs.pop('post_id')
        if lookup_kwargs and not force_download:
            try:
                # See if we can get the object from the database just from the
                # parameters
                obj = cls.object_class.objects.get(**lookup_kwargs)
                return cls(obj)
            except (cls.object_class.DoesNotExist, cls.object_class.MultipleObjectsReturned):
                pass
        # Either this doesn't exist in the database, we can't uniquely
        # determine the object from the URL parameters, or we simply need to
        # refetch it for validation purposes, so fetch it from the forums
        obj = cls.object_class(**kwargs)
        page = cls(obj, get_soup(url) if url else None)
        page.load_object(save, object_type)
        return page

    @classmethod
    def get_params_from_url(cls, url):
        """
        Extracts relevant parameters from a forum URL.

        """
        for regex in cls.object_id_regexen:
            url_regex = re.compile(r'^(?:https?://(?:www\.)?%s|/(?:index\.php\?)?)?%s' % (re.escape(settings.FORUM_URL), regex), re.U)
            match = url_regex.match(url)
            if match and match.group(1):  # The URL is invalid if the object ID match is zero-length
                return match.groupdict()
        else:
            raise ValueError(u"Invalid %s URL (%s)." % (cls.__name__, url))

    def load_object(self, save=True, object_type=None):
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


class ForumObject(object):
    """
    A base class mixin for forum objects.

    """
    _page = None

    @classmethod
    def get_page_class(self):
        """
        Returns the page class for this object type.

        """
        return ForumPage

    def get_page(self):
        """
        Returns a ForumPage instance corresponding to this object.

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


class Member(ForumObject, models.Model):
    user_id = models.PositiveIntegerField(unique=True, primary_key=True)
    username = models.CharField(max_length=50)

    objects = MemberQuerySet.as_manager()

    class Meta:
        ordering = ['username']

    def __str__(self):
        return self.username

    def to_dict(self):
        return {'type': 'nominee', 'pk': self.pk, 'name': str(self), 'object': {'username': self.username}}

    def link(self):
        return u"https://%smembers/%s/" % (settings.FORUM_URL, self.user_id)

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


class MemberPage(ForumPage):
    object_id_regexen = [r'members/(?:[^&.]*\.)?(?P<user_id>\d+)']
    object_class = Member

    @classmethod
    def from_params(self, save=False, force_download=False, url=None, object_type=None, **kwargs):
        if not url.endswith('/about/'):
            # Trim off fragment identifier, if any
            # Allows app to accept e.g. https://forums.example.com/index.php?members/negrek.1/#about
            if url.rfind('#') > -1:
                url = url[:url.rfind('#')]
            url += '/about/'
        return super(MemberPage, self).from_params(save, force_download, url, object_type, **kwargs)

    def get_bio(self):
        soup = self.get_soup()
        # First check whether we're able to see the page at all
        if soup.find('div', class_=u'blockMessage--error', string=re.compile('You must be logged-in')):
            raise ValidationError(u"Could not access profile page. Refer to the validation instructions and make your profile visible to all visitors. If you have already done so, please contact Dragonfree on the forums with your username so that you can be manually verified.")

        try:
            bio = soup.find('div', class_='p-body-pageContent').find(class_='block-row').find(class_='bbWrapper')
        except AttributeError:
            raise ValidationError(u"Could not find About field on profile page. If you submitted a valid profile link, please contact Dragonfree on the forums with your username so that you can be manually verified.")
        return str(bio.get_text())

    def load_object(self, save=True, object_type=None):
        soup = self.get_soup()
        username = soup.find('h1', class_=u"p-title-value").text
        self.object.username = username
        self.object._page = self
        if save:
            self.object.save()
        return self.object


def get_verification_code():
    return User.objects.make_random_password()


class User(AbstractUser):
    """
    A user object, not to be confused with a forum member.

    In order to do much of anything, users need to associate their
    account with a forum member (the member field). This is done
    either by verifying ownership of a forum account (in which case
    verified is True) or by registering a temporary account as that
    member (in which case verified is False, until the user is manually
    verified by an admin).

    """
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, blank=True, null=True)
    verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=10, default=get_verification_code)

    def validate_verification_code(self, page):
        if self.verification_code not in page.get_bio():
            raise ValidationError(u"Your verification code was not found in your profile's About section. Please ensure you followed the instructions correctly. If the problem persists, please contact an admin on the forums to be manually verified.")
        # Ensure each verification can be used only once
        self.verification_code = get_verification_code()
        self.save()


class Genre(models.Model):
    """A fic genre."""
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class FicQuerySet(models.QuerySet):
    def nominated_in_year(self, year):
        return self.filter(nominations__year=year).distinct()


class FicManager(models.Manager):
    def get_queryset(self):
        return FicQuerySet(self.model, using=self._db).prefetch_related('authors')

    def nominated_in_year(self, year):
        return self.get_queryset().nominated_in_year(year)


class Fic(ForumObject, models.Model):
    """
    A fic, defined by its forum thread and possibly post ID.

    """
    title = models.CharField(max_length=255)
    authors = models.ManyToManyField(Member, related_name='fics')
    thread_id = models.PositiveIntegerField()
    post_id = models.PositiveIntegerField(blank=True, null=True)
    posted_date = models.DateTimeField()
    summary = models.TextField(blank=True)
    genres = models.ManyToManyField(Genre, blank=True, related_name='fics')
    completed = models.BooleanField(default=False)
    related_fics = models.ManyToManyField('self', blank=True)

    objects = FicManager()

    _authors = []
    _tags = []

    class Meta:
        unique_together = ['thread_id', 'post_id']
        ordering = ['title', 'thread_id', 'post_id']

    def __str__(self):
        if self.pk is not None:
            authors = [author.username for author in self.authors.all()]
        else:
            authors = [author.username for author in self._authors]
        return u"%s by %s" % (self.title, pretty_join(authors))

    def to_dict(self):
        return {'type': 'fic', 'pk': self.pk, 'name': str(self), 'object': {'title': self.title, 'authors': [author.pk for author in self.authors.all()]}}

    def get_authors(self):
        return list(self.authors.all()) if self.pk else self._authors

    def link(self):
        if self.post_id:
            urlbit = u"posts/%s" % self.post_id
        else:
            urlbit = u"threads/%s" % self.thread_id
        return u"https://%s%s/" % (settings.FORUM_URL, urlbit)

    def link_html(self):
        return u'<a href="%s" target="_blank">%s</a> by %s' % (self.link(), self.title, pretty_join([author.link_html() for author in self.authors.all()]))

    def link_bbcode(self):
        return u'[url=%(link)s]%(title)s[/url] by %(authors)s' % {'link': self.link(), 'id': self.post_id or self.thread_id, 'title': self.title, 'authors': pretty_join([author.link_bbcode() for author in self.authors.all()])}

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
            # We're only adding authors here, rather than simply overriding,
            # because that means if an admin adds a coauthor, they won't be
            # overwritten next time we load the fic. Kind of a hack, but it
            # works for now.
            existing_authors = self.authors.all()
            self.authors.add(*[author for author in self._authors if author not in existing_authors])
        if self._tags:
            FicTag.objects.filter(~Q(tag__in=self._tags), fic=self).delete()
            for tag in self._tags:
                if not FicTag.objects.filter(fic=self, tag=tag).exists():
                    FicTag.objects.create(fic=self, tag=tag)


class FicPage(ForumPage):
    # Matches URL queries for threads/posts including
    # - threads/<threadid>/
    # - threads/<threadid>/unread
    # - threads/fic-title.<threadid>/
    # - threads/<threadid>/#post-<postid>
    # - threads/<threadid>/page-2#post-<postid>
    # - posts/<postid>/
    # ...which should cover every sensible URL a person could enter for a
    # XenForo thread/post.
    object_id_regexen = [
        r'threads/(?:[^&.]*\.)?(?P<thread_id>\d+)(?:/page-\d+|/unread)?/?(?:#?post-(?P<post_id>\d+))?',
        r'posts/(?P<post_id>\d+)'
    ]
    object_class = Fic

    _pagination = None

    def get_pagination(self):
        if not self._pagination:
            soup = self.get_soup()
            self._pagination = soup.find('nav', class_="pageNavWrapper")
        return self._pagination

    def get_page(self, page_link):
        page = FicPage.from_url(u"https://{}{}".format(settings.FORUM_URL.rsplit('/', 1)[0], page_link['href']), force_download=True)
        # Override the object (but not the soup)
        page.object = self.object
        return page

    def get_last_page(self):
        pagination = self.get_pagination()
        if pagination is None:
            return self
        page_links = [link for link in pagination.ul.find_all('li') if "pageNav-page--skip" not in link['class']]
        last_page_link = page_links[-1].a if page_links else None

        if last_page_link:
            return self.get_page(last_page_link)
        else:
            return self

    def has_pages(self):
        pagination = self.get_pagination()
        return bool(pagination)

    def has_next_page(self):
        pagination = self.get_pagination()
        if pagination is None:
            return False
        nextlink = pagination.find('a', class_="pageNav-jump--next")
        return bool(nextlink)

    def has_prev_page(self):
        pagination = self.get_pagination()
        if pagination is None:
            return False
        prevlink = pagination.find('a', string="pageNav-jump--prev")
        return bool(prevlink)

    def get_page_number(self):
        pagination = self.get_pagination()
        if pagination is None:
            return 1
        pagelink = pagination.find('a', class_="currentPage")
        if pagelink:
            return int(pagelink.get_text(strip=True))
        else:
            return 1

    def get_next_page(self):
        pagination = self.get_pagination()
        if pagination is None:
            return None
        nextlink = pagination.find('a', class_="pageNav-jump--next")
        if nextlink:
            return self.get_page(nextlink)
        else:
            return None

    def get_prev_page(self):
        pagination = self.get_pagination()
        if pagination is None:
            return None
        prevlink = pagination.find('a', string="pageNav-jump--prev")
        if prevlink:
            return self.get_page(prevlink)
        else:
            return None

    def get_post(self):
        if self.object.post_id:
            return Post(self, self.get_soup().find(id="js-post-%s" % self.object.post_id))
        else:
            return Post(self, self.get_soup().find(class_="block--messages").article)

    def get_page_posts(self):
        soup = self.get_soup()
        return [Post(self, post) for post in soup.find(class_="block--messages").find_all('article', class_="message--post")]

    def is_fic(self):
        forum_link = self.get_soup().find(class_="p-breadcrumbs").find_all('li')[-1].a
        return forum_link['href'] in settings.VALID_FIC_FORUMS

    def load_object(self, save=True, object_type=None):
        if self.object.thread_id is None and self.object.post_id is None:
            raise ValidationError(u"No parameters given.")

        soup = self.get_soup()

        if not self.is_fic():
            raise ValidationError(u"This thread (%s) does not seem to be a fanfic (it is not located in the fanfic forum). Please enter the link to a valid fanfic." % self.object.link())

        thread_title = soup.find('h1', class_="p-title-value").find(text=True, recursive=False)

        if self.object.thread_id is None:
            thread_link = soup.find(class_="message-attribution-main").a
            self.object.thread_id = FicPage.get_params_from_url(thread_link['href'])['thread_id']

        if object_type != 'post':
            self.object.post_id = None

        post = self.get_post()

        if self.object.post_id is not None and post.post_id != int(self.object.post_id) or self.object.post_id is None and self.get_page_number() != 1:
            # We're on the wrong page! We don't actually want to load
            # information from this page - it's not safe (we'll get the wrong
            # information).
            if save:
                # We really want to load this object. Fetch it again altogether
                # (from params).
                self.object = FicPage.from_params(save=True, thread_id=self.object.thread_id, post_id=self.object.post_id, object_type=object_type).object
            return self.object

        if self.object.post_id is not None:
            # The fic starts in a particular post - use a placeholder title
            title = u"%s - post %s" % (thread_title, self.object.post_id)
        else:
            # The fic is a thread - just use the thread title as is
            title = thread_title

        self.object.title = title
        self.object.posted_date = post.posted_date
        self.object._authors = [post.author]
        self.object._page = self
        if save:
            self.object.save()
        return self.object


class FicTag(models.Model):
    """A tag for a fic."""

    tag = models.CharField(max_length=50, db_index=True)
    fic = models.ForeignKey(Fic, related_name='tags', on_delete=models.CASCADE)

    def __unicode__(self):
        return self.tag


class Post(object):
    def __init__(self, page, post_soup):
        self.page = page
        self._soup = post_soup

    def __str__(self):
        return u'Post #{} by {} in {} (posted {})'.format(self.post_id, self.author, self.page.object, self.posted_date)

    def __repr__(self):
        return u'<{}>'.format(self)

    @property
    def post_id(self):
        return int(self._soup['id'][8:])

    @property
    def posted_date(self):
        date_elem = self._soup.find(class_="message-attribution-main").time

        return datetime.fromtimestamp(int(date_elem['data-time']), utc)

    @property
    def body_text(self):
        post_body = self._soup.find(class_="message-body")
        for blockquote in post_body.find_all("blockquote"):
            blockquote.decompose()
        return post_body.get_text()

    @property
    def word_count(self):
        return len(self.body_text.split())

    @property
    def author(self):
        user_elem = self._soup.find('h4', class_="message-name")
        if user_elem.a:
            # It's a registered user's linked username
            username = user_elem.a.get_text(strip=True)
            try:
                user_id = int(MemberPage.get_params_from_url(user_elem.a['href'])['user_id'])
            except ValueError:
                # It's a deleted post and we can't get a proper URL - let's make it a guest.
                user_id = None
        else:
            # It's (presumably) a guest
            username = user_elem.span.get_text(strip=True)
            user_id = None
        member, created = Member.objects.get_or_create(user_id=user_id, defaults={"username": username})
        return member

    @property
    def threadmark_title(self):
        threadmark_elem = self._soup.find(class_="threadmarkLabel")
        return threadmark_elem.get_text() if threadmark_elem else ""


class PostPage(FicPage):
    object_id_regexen = (
        r'threads/(?:[^&.]*\.)?(?:\d+)(?:/page-\d+|/unread)?/?(?:#?post-(?P<post_id>\d+))',
        r'posts/(?P<post_id>\d+)'
    )

    @classmethod
    def from_params(cls, save=False, force_download=False, url=None, object_type=None, **kwargs):
        return super().from_params(save, force_download, url, 'post', **kwargs)

    def load_object(self, save=True, object_type=None):
        soup = self.get_soup()

        if not self.is_fic():
            raise ValidationError(u"This post (%s) does not seem to be in a valid fanfic (it is not located in the fanfic forum). Please enter the link to a valid post." % self.object.link())

        post = self.get_post()
        self.object.author = post.author
        self.object.posted_date = post.posted_date
        self.object.word_count = post.word_count
        if hasattr(self.object, 'threadmark_title'):
            self.object.threadmark_title = post.threadmark_title

        thread_params = FicPage.get_params_from_url(soup.find(class_="message-attribution-main").a["href"])
        self.object.fic = FicPage.from_params(thread_id=thread_params["thread_id"], save=True).object

        self.object.chapters = 1
        if save:
            self.object.save()

        return self.object


class Review(ForumObject, models.Model):
    post_id = models.PositiveIntegerField(unique=True, primary_key=True)
    author = models.ForeignKey(Member, related_name='reviews', on_delete=models.PROTECT)
    fic = models.ForeignKey(Fic, related_name='reviews', on_delete=models.PROTECT)
    posted_date = models.DateTimeField()
    word_count = models.PositiveIntegerField()
    chapters = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("author", "post_id")

    def __str__(self):
        return "{}'s review on {}".format(self.author, self.fic.title)

    def link(self):
        return f"https://{settings.FORUM_URL}posts/{self.post_id}/"

    def link_html(self):
        return f'<a href="{self.link()}">{self}</a>'

    def link_bbcode(self):
        return f"[url={self.link()}]{self}[/url]"

    @classmethod
    def get_page_class(self):
        return ReviewPage


class ReviewPage(PostPage):
    object_class = Review

    def load_object(self, save=True, object_type=None):
        self.object = super(ReviewPage, self).load_object(save=False)

        self.object.chapters = 1
        if save:
            self.object.save()

        return self.object


class Chapter(models.Model):
    """A chapter of a fic."""

    post_id = models.PositiveIntegerField(unique=True, primary_key=True)
    fic = models.ForeignKey(Fic, related_name='chapters', on_delete=models.CASCADE)
    threadmark_title = models.CharField(max_length=255)
    posted_date = models.DateTimeField()
    word_count = models.PositiveIntegerField()

    class Meta:
        ordering = ('fic', 'posted_date')

    def __str__(self):
        return "{}: {}".format(self.fic.title, self.threadmark_title) or "{}: post #{}".format(self.fic.title, self.post_id)

    def link(self):
        return f"https://{settings.FORUM_URL}posts/{self.post_id}/"

    def link_html(self):
        return f'<a href="{self.link()}">{self}</a>'

    def link_bbcode(self):
        return f"[url={self.link()}]{self}[/url]"

    @classmethod
    def get_page_class(self):
        return ChapterPage


class ChapterPage(PostPage):
    object_class = Chapter

    def load_object(self, save=True, object_type=None):
        self.object = super(ChapterPage, self).load_object(save=False)

        if self.object.author not in self.object.fic.get_authors():
            raise ValidationError(u"This post (%s) does not seem to be by an author of the thread it is in. If this is in error, please contact Thousand Roads staff." % self.object.link())

        if save:
            self.object.save()

        return self.object
