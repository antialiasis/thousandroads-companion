# -*- coding: utf8 -*-
from datetime import datetime
from functools import total_ordering
from django.db import models
from django.db.models import Q, Count, Prefetch
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from serebii.models import Member, Fic, User
from serebii.utils import bbcode_to_html


CURRENT_YEAR = settings.YEAR

ELIGIBILITY_START = datetime(int(CURRENT_YEAR), 1, 1, 0, 0, tzinfo=timezone.utc)
ELIGIBILITY_END = datetime(int(CURRENT_YEAR) + 1, 1, 1, 0, 0, tzinfo=timezone.utc)
ELIGIBILITY_ERROR_MESSAGE = u"This fanfic is not eligible for this year's awards. Please nominate a story posted/updated between 00:00 UTC January 1st {year} and 23:59 UTC December 31st {year}.".format(year=CURRENT_YEAR)


def check_in_awards_year(date):
    """
    Returns True if the given date is within the current year (UTC).

    """
    if date < ELIGIBILITY_END and date >= ELIGIBILITY_START:
        return True
    else:
        return False


def validate_fic_page(posts):
    """
    Returns True if any of the given posts was posted within the
    current year.

    """
    return any(check_in_awards_year(post.posted_date) for post in posts)


def validate_post_fic(page):
    """
    Returns True if the given FicPage for a post fic was posted in the
    current year (and thus is eligible for nomination), or False
    otherwise.

    """
    # Make sure this was posted in the awards year
    return check_in_awards_year(page.get_post().posted_date)


def validate_thread_fic(page):
    """
    Returns True if the given FicPage was likely updated in the current
    year (and thus is eligible for nomination), or False otherwise.

    """
    # We need to check whether the 'fic was UPDATED in the awards year.
    # First look at author's posts on the given page.
    # If any are from the awards year, we don't need to go further.
    author_ids = [author.user_id for author in page.object.get_authors()]
    authorposts = [post for post in page.get_page_posts() if post.author.user_id in author_ids]

    if not validate_fic_page(authorposts):
        if not page.has_pages():
            # This is the only page!
            # The story can't possibly be eligible.
            return False

        elif not page.has_prev_page():
            # This is the first page!
            if authorposts[0].posted_date >= ELIGIBILITY_END:
                # If the first post was made after the end of the awards year,
                # the story can't possibly be eligible.
                return False

        elif not page.has_next_page():
            # This is the last page!
            # I don't believe this should be able to happen
            # But just in case...
            if authorposts[-1].posted_date < ELIGIBILITY_START:
                # If the last post was made before the beginning of the awards
                # year, the story can't possibly be eligible.
                return False

        # Nothing for it but to start working backward through the thread
        # First, fetch the last page if we aren't there already
        curpage = page.get_last_page()
        if curpage is page:
            curpage = curpage.get_prev_page()

        while curpage:
            authorposts = [post for post in curpage.get_page_posts() if post.author.user_id in author_ids]

            if not validate_fic_page(authorposts):
                # If the author's first post on this page is from before the
                # awards year, the story can't possibly be eligible (if we go
                # further back in the thread, we're just going to get even
                # older posts).
                if authorposts[0].posted_date < ELIGIBILITY_START:
                    return False

                curpage = curpage.get_prev_page()
            else:
                break

    return True


def check_eligible(page):
    """
    Check if the given SerebiiPage is eligible to be nominated (this year).

    """
    # Only fics do actual eligibility checks at the moment
    if not isinstance(page.object, Fic):
        return True

    fic = page.object

    # First, check the eligibility cache
    cached_eligible = FicEligibility.objects.get_eligible(fic.thread_id, fic.post_id)
    eligible = cached_eligible

    if cached_eligible is None:
        # We didn't have eligibility info; figure out if the fic is
        # actually eligible
        if fic.posted_date and check_in_awards_year(fic.posted_date):
            # If the posted_date is within the awards year, then the fic
            # must be eligible
            eligible = True
        elif Nomination.objects.from_year().filter(fic=fic).exists():
            # Otherwise, is the fic already nominated? Then we must have
            # already checked it for eligibility
            eligible = True
        else:
            # Do the full eligibility check
            eligible = validate_post_fic(page) if fic.post_id else validate_thread_fic(page)

        # Save the info we just fetched in the eligibility cache, but
        # only if we're past the awards year (otherwise the fic could
        # later become eligible for this year)
        if timezone.now().year > settings.YEAR:
            FicEligibility.objects.set_eligible(eligible, fic.thread_id, fic.post_id)

    if not eligible:
        raise ValidationError(ELIGIBILITY_ERROR_MESSAGE)
    else:
        # We don't know if this user is actually allowed to nominate this
        # But it is eligible! Save it so it gets added to the list of eligible fics
        fic.save()


def verify_current(member):
    """
    Find any current nominations/votes by this member and verify them.
    Should be run when a member is verified.

    """
    phase = Phase.get_current()
    if phase == 'nomination':
        Nomination.objects.from_year().filter(member=member, verified=False).update(verified=True)
    elif phase == 'voting':
        Vote.objects.from_year().filter(member=member, verified=False).update(verified=True)


@total_ordering
class Phase(object):
    """
    Simple helper class to keep track of phases. Mostly here for the
    implementation of __cmp__, which allows us to compare phases
    chronologically (for instance, nomination < voting).

    """
    _phases = [None, 'nomination', 'voting', 'finished']

    def __init__(self, phase):
        if phase in self._phases:
            self.phase = phase
        else:
            raise ValueError(u"%s is not a valid phase." % phase)

    def __eq__(self, other):
        if not isinstance(other, Phase):
            other = Phase(other)
        return self._phases.index(self.phase) == self._phases.index(other.phase)

    def __lt__(self, other):
        if not isinstance(other, Phase):
            other = Phase(other)
        return self._phases.index(self.phase) < self._phases.index(other.phase)

    def __str__(self):
        return str(self.phase)

    def __hash__(self):
        return hash(self.phase)

    def __bool__(self):
        return bool(self.phase)

    @classmethod
    def get_current(cls):
        try:
            return cls(settings.PHASE)
        except AttributeError:
            # Determine the phase by the current date and the deadline settings
            now = datetime.utcnow()

            if settings.VOTING_END and now > settings.VOTING_END:
                return cls('finished')
            if settings.VOTING_START and now > settings.VOTING_START:
                return cls('voting')
            if settings.NOMINATION_START and now > settings.NOMINATION_START:
                return cls('nomination')
            return cls(None)


class YearlyManager(models.Manager):
    def from_year(self, year=None):
        return super(YearlyManager, self).filter(year=year or CURRENT_YEAR)


class YearlyData(models.Model):
    """
    An abstract base class for entities that exist per-year: the
    awards, nominations and votes for that year's awards. All it
    does is add a year field and use the YearlyManager, which allows
    for easy querying of objects from the appropriate year.

    """
    year = models.PositiveIntegerField(validators=[
        MinValueValidator(settings.MIN_YEAR),
        MaxValueValidator(settings.MAX_YEAR)
    ], db_index=True, default=CURRENT_YEAR)

    objects = YearlyManager()

    class Meta:
        abstract = True


class Category(models.Model):
    """
    An award category, such as "Overall Fic Awards" or "Reviewer
    Awards". Not to be confused with when we colloquially refer to
    e.g. "Best Pokémon Chaptered Fic" as a category - that's the
    Award model. Yes, this is a bit confusing.

    """
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = u"categories"
        ordering = ('id',)

    def __str__(self):
        return self.name


class Award(models.Model):
    """
    An actual award people can nominate for, such as "Best Pokémon
    Chaptered Fic" or "Funniest Scene".

    The has_ fields define the format of nominations for this award: if
    it expects nominations to include a person (only applies for non-
    fic awards, since otherwise the fic's author is automatically the
    nominated person), fic (any award that does nominate a fic), detail
    (such as a scene or the name of a character) and/or samples (links
    to sample posts for e.g. reviewer awards). This allows for some
    flexibility for future awards.

    The requires_new field, and potentially new fields to be added in
    the future, defines whether nominations must be "new", that is, new
    this awards year.

    """
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    has_person = models.BooleanField(default=False)
    has_fic = models.BooleanField(default=False)
    has_detail = models.BooleanField(default=False)
    has_samples = models.BooleanField(default=False)
    requires_new = models.BooleanField(default=False)
    detail_character_limit = models.PositiveIntegerField(blank=True, null=True)
    display_order = models.PositiveIntegerField(blank=True)

    class Meta:
        ordering = ('category', 'display_order', 'pk')

    def __str__(self):
        return self.name

    def clean(self):
        if not self.has_person and not self.has_fic:
            raise ValidationError(u"An award must be for either a fic or a person.")

    def save(self, *args, **kwargs):
        if self.display_order is None:
            max_display_order = Award.objects.filter(category=self.category).aggregate(max_display_order=models.Max('display_order')).get('max_display_order')
            if max_display_order:
                self.display_order = max_display_order + 1
            else:
                self.display_order = 0
        return super(Award, self).save(*args, **kwargs)


class NominationSet(object):
    """
    A set of identical nominations to be regarded as one. The point of
    this is to combine e.g. Person A's nomination for Pokémon
    Revelation: Cross of Fates for Best Pokémon Chaptered Fic with
    Person B's nomination for Pokémon Revelation: Cross of Fates for
    Best Pokémon Chaptered Fic, so that Pokémon Revelation: Cross of
    Fates will only appear once in the nomination list and voting form.

    The identicalness of the nominations is assumed, but not enforced.
    Thus, in practice, the NominationSet routes most attribute access
    to the first nomination in the set. All it needs to do other than
    that is simply to allow adding a nomination to the set and getting
    the nominator details and votes for all the nominations in the set.

    """
    def __init__(self, nomination=None):
        self.nominations = []
        if nomination:
            self.nominations.append(nomination)

    def get_nominator_details(self):
        return [{
            'member': nomination.member,
            'comment': nomination.comment,
            'link': nomination.link
        } for nomination in self.nominations]

    def add(self, nomination):
        self.nominations.append(nomination)

    def get_votes(self):
        return sum(len(nomination.votes.all()) for nomination in self.nominations)

    @property
    def modified_date(self):
        return max(nomination.modified_date for nomination in self.nominations)

    def __getattr__(self, name):
        return getattr(self.nominations[0], name)


class YearAwardManager(YearlyManager):
    def get_with_distinct_nominations(self, year=None, with_votes=False):
        """
        Fetches awards for a given year along with the nominations for
        each of them, in the form of NominationSets that eliminate
        duplicates.

        """
        year_awards = self.from_year(year).prefetch_related('award__category')
        for year_award in year_awards:
            year_award.distinct_nominations = []
            for nomination in year_award.get_nominations(with_votes):
                for existing_nominations in year_award.distinct_nominations:
                    if not nomination.is_distinct_from(existing_nominations):
                        existing_nominations.add(nomination)
                        break
                else:
                    year_award.distinct_nominations.append(NominationSet(nomination))
        return year_awards


class YearAward(YearlyData):
    """
    The specific instance of an award that exists for a given year.
    So, for example, 2014's Best Pokémon Chaptered Fic is a YearAward.
    This model mostly exists to define which awards are active in a
    given year at the moment; we might eventually move, say, the award
    display order to this model, though, if in the future we want to
    change that for some years.

    """
    award = models.ForeignKey(Award, on_delete=models.CASCADE)

    objects = YearAwardManager()

    class Meta:
        unique_together = ('year', 'award')
        ordering = ('-year', 'award__category', 'award__display_order')

    def __str__(self):
        return u"%s - %s awards" % (self.award, self.year)

    def get_nominations(self, with_votes=False):
        nominations = Nomination.objects.from_year(self.year).filter(verified=True, award=self.award).distinct()
        if with_votes:
            nominations = nominations.prefetch_related(Prefetch('votes', Vote.objects.filter(verified=True).distinct()))
            nominations = sorted(nominations, key=lambda nomination: len(nomination.votes.all()), reverse=True)
        return nominations


class Nomination(YearlyData):
    """
    A nomination for an award. Note that the 'member' field is the
    nominator, i.e. the person who made the nomination, whereas the
    nominee is the person who is nominated (for non-fic awards).

    """
    award = models.ForeignKey(Award, related_name='nominations', on_delete=models.CASCADE)
    member = models.ForeignKey(Member, related_name='nominations_by', on_delete=models.CASCADE)
    nominee = models.ForeignKey(Member, blank=True, null=True, related_name='nominations', on_delete=models.CASCADE)
    fic = models.ForeignKey(Fic, blank=True, null=True, related_name='nominations', on_delete=models.CASCADE)
    detail = models.TextField(blank=True, help_text=u"The character(s), scene or quote that you want to nominate.")
    link = models.URLField(blank=True, null=True, help_text=u"A link to a sample (generally a post) illustrating your nomination.")
    comment = models.TextField(blank=True, help_text=u"Optionally, you may write a comment explaining why you feel this nomination deserves the award. Users will be able to see this on the voting form. Basic BBCode allowed.")
    modified_date = models.DateTimeField(auto_now=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return u"{award} ({year}): {nomination} ({member})".format(
            award=self.award,
            year=self.year,
            nomination=self.nomination_text(),
            member=self.member
        )

    def clean(self):
        if self.award.has_fic and not self.fic:
            raise ValidationError(u"You must nominate a valid fic for this award.")

        if self.award.has_person and not self.nominee:
            raise ValidationError(u"You must nominate a valid person for this award.")

        if self.award.has_detail and not self.detail:
            raise ValidationError(u"You must nominate a valid character/quote/scene for this award.")

        if self.award.has_samples and not self.link:
            raise ValidationError(u"You must provide a sample link for this award.")

        if self.nominee == self.member or self.fic and self.member in self.fic.authors.all():
            raise ValidationError(u"You cannot nominate yourself or your own work.")

        if self.award.requires_new and self.award.has_fic and self.fic.posted_date and self.fic.posted_date.year != settings.YEAR:
            raise ValidationError(u"Only stories posted after January 1st, %s UTC are eligible for this award." % settings.YEAR)

        if self.award.has_detail and self.award.detail_character_limit is not None and len(self.detail) > self.award.detail_character_limit:
            raise ValidationError(
                u"The text you have nominated is %s characters long. The limit is %s characters. Please pick a shorter excerpt." % (
                    len(self.detail),
                    self.award.detail_character_limit
                )
            )

    def is_distinct_from(self, nomination):
        """
        Returns True if this nomination is different from the given
        nomination and False otherwise.

        """
        distinguishing_fields = []
        if self.award.has_fic:
            distinguishing_fields.append('fic')
        if self.award.has_person:
            distinguishing_fields.append('nominee')
        if self.award.has_detail:
            distinguishing_fields.append('detail')
        for field in distinguishing_fields:
            if getattr(self, field) != getattr(nomination, field):
                return True
        return False

    def nomination_text(self):
        if self.detail:
            if self.fic:
                return u"%s from %s" % (self.detail_text(), self.fic)
            else:
                return u"%s - %s" % (self.detail_text(), self.nominee)
        else:
            if self.fic:
                return str(self.fic)
            else:
                return str(self.nominee)

    def nomination_bbcode(self):
        if self.detail:
            if not self.has_long_detail():
                if self.fic:
                    return u"%s, %s" % (self.detail, self.fic.link_bbcode())
                else:
                    return u"%s - %s" % (self.detail, self.nominee.link_bbcode())
            else:
                return u"[spoiler]%s[/spoiler]%s" % (self.detail, self.fic.link_bbcode() if self.fic else self.nominee.link_bbcode())
        else:
            if self.fic:
                return self.fic.link_bbcode()
            else:
                return self.nominee.link_bbcode()

    def nomination_html(self):
        if self.detail:
            if not self.has_long_detail():
                if self.fic:
                    return u"%s, %s" % (self.detail_html(), self.fic.link_html())
                else:
                    return u"%s - %s" % (self.detail_html(), self.nominee.link_html())
            else:
                return u'%s<blockquote class="detail">%s</blockquote>' % (self.fic.link_html() if self.fic else self.nominee.link_html(), self.detail_html())
        else:
            if self.fic:
                return self.fic.link_html()
            else:
                return self.nominee.link_html()

    def detail_text(self):
        if not self.detail:
            return None
        elif len(self.detail) <= 100:
            return self.detail
        else:
            return self.detail[:100] + "[...]"

    def has_long_detail(self):
        return self.detail and len(self.detail) > 100

    def detail_html(self):
        if not self.detail:
            return None
        return bbcode_to_html(self.detail)


class Vote(YearlyData):
    """
    A vote for a nomination by a member. Technically the award field
    is redundant, since the nomination is connected to an award,
    but it's there so that we can enforce uniqueness on it.

    """
    member = models.ForeignKey(Member, related_name='votes', on_delete=models.CASCADE)
    award = models.ForeignKey(Award, related_name='votes', on_delete=models.CASCADE)
    nomination = models.ForeignKey(Nomination, related_name='votes', on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ('member', 'award', 'year')

    def __str__(self):
        return u"Vote for %s in %s by %s" % (self.nomination.nomination_text(), self.award, self.member)

    def clean(self):
        if self.nomination.award != self.award:
            raise ValidationError(u"This nomination is not for this award.")
        if self.nomination.nominee == self.member or self.nomination.fic and self.member in self.nomination.fic.authors.all():
            raise ValidationError(u"You cannot vote for yourself.")


class EligibilityManager(models.Manager):
    def get_eligible(self, thread_id, post_id=None, year=CURRENT_YEAR):
        entry = self.filter(thread_id=thread_id, post_id=post_id, year=year).first()
        if entry is None:
            return None
        else:
            return entry.is_eligible

    def set_eligible(self, eligible, thread_id, post_id=None, year=CURRENT_YEAR):
        return self.update_or_create(thread_id=thread_id, post_id=post_id, year=year, defaults={'is_eligible': eligible})


class FicEligibility(YearlyData):
    """
    An eligibility result for a given fic in a given year. The fic does
    not have to actually exist in the database; this allows for
    cached eligibility checks for fics that never get created.

    """
    thread_id = models.PositiveIntegerField()
    post_id = models.PositiveIntegerField(blank=True, null=True)
    is_eligible = models.BooleanField()

    objects = EligibilityManager()

    class Meta:
        unique_together = ('thread_id', 'post_id', 'year')
        verbose_name_plural = 'fic eligibilities'

    def __str__(self):
        return u"Eligibility result for thread %s in %s: %s" % (self.thread_id if self.post_id is None else u"%s post %s" % (self.thread_id, self.post_id), self.year, self.is_eligible)


class PageViewManager(models.Manager):
    def add_pageview(self, user, page):
        return self.update_or_create(user=user, page=page, defaults={})

    def get_last_pageview(self, user, page):
        pageview = self.filter(user=user, page=page).first() if user.is_authenticated else None
        return pageview.viewed_time if pageview else timezone.now()


class PageView(models.Model):
    """
    A page view, used to keep track of when a user last viewed a page
    so that we can show a "New" badge for new nominations/votes.

    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    page = models.CharField(max_length=20)
    viewed_time = models.DateTimeField(auto_now=True)

    objects = PageViewManager()

    class Meta:
        unique_together = ('user', 'page')

    def __str__(self):
        return u"%s viewed %s at %s" % (self.user, self.page, self.viewed_time)
