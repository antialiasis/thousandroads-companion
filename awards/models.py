# -*- coding: utf8 -*-
import bbcode
from datetime import datetime
from django.db import models
from django.db.models import Q, Count, Prefetch
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from serebii.models import Member, Fic, User


CURRENT_YEAR = settings.YEAR


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

    def __cmp__(self, other):
        if not isinstance(other, Phase):
            other = Phase(other)
        return cmp(self._phases.index(self.phase), self._phases.index(other.phase))

    def __unicode__(self):
        return self.phase

    def __str__(self):
        return self.phase

    def __hash__(self):
        return hash(self.phase)

    def __nonzero__(self):
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
    year = models.PositiveIntegerField(validators=[MinValueValidator(settings.MIN_YEAR), MaxValueValidator(settings.MAX_YEAR)], db_index=True, default=CURRENT_YEAR)

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

    def __unicode__(self):
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
    category = models.ForeignKey(Category)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    has_person = models.BooleanField(default=False)
    has_fic = models.BooleanField(default=False)
    has_detail = models.BooleanField(default=False)
    has_samples = models.BooleanField(default=False)
    requires_new = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(blank=True)

    class Meta:
        ordering = ('category', 'display_order', 'pk')

    def __unicode__(self):
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
    award = models.ForeignKey(Award)

    objects = YearAwardManager()

    class Meta:
        unique_together = ('year', 'award')
        ordering = ('-year', 'award__category', 'award__display_order')

    def __unicode__(self):
        return u"%s - %s awards" % (self.award, self.year)

    def get_nominations(self, with_votes=False):
        nominations = Nomination.objects.from_year(self.year).filter(Q(member__user__isnull=True) | Q(member__user__verified=True), award=self.award).distinct()
        if with_votes:
            nominations = nominations.prefetch_related(Prefetch('votes', Vote.objects.filter(member__user__verified=True).distinct()))
            nominations = sorted(nominations, key=lambda nomination: len(nomination.votes.all()), reverse=True)
        return nominations


class Nomination(YearlyData):
    """
    A nomination for an award. Note that the 'member' field is the
    nominator, i.e. the person who made the nomination, whereas the
    nominee is the person who is nominated (for non-fic awards).

    """
    award = models.ForeignKey(Award, related_name='nominations')
    member = models.ForeignKey(Member, related_name='nominations_by')
    nominee = models.ForeignKey(Member, blank=True, null=True, related_name='nominations')
    fic = models.ForeignKey(Fic, blank=True, null=True, related_name='nominations')
    detail = models.TextField(blank=True, help_text=u"The character(s), scene or quote that you want to nominate.")
    link = models.URLField(blank=True, null=True, help_text=u"A link to a sample (generally a post) illustrating your nomination.")
    comment = models.TextField(blank=True, help_text=u"Optionally, you may write a comment explaining why you feel this nomination deserves the award. Users will be able to see this on the voting form. Basic BBCode allowed.")
    modified_date = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"%s nominated for %s in %s" % (self.nomination_text(), self.award, self.year)

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
                return unicode(self.fic)
            else:
                return unicode(self.nominee)

    def nomination_bbcode(self):
        if self.detail:
            if not self.has_long_detail():
                if self.fic:
                    return u"%s, %s" % (self.detail, self.fic.link_bbcode())
                else:
                    return u"%s - %s" % (self.detail, self.nominee.link_bbcode())
            else:
                return u"[spoil]%s[/spoil]%s" % (self.detail, self.fic.link_bbcode() if self.fic else self.nominee.link_bbcode())
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
        return bbcode.render_html(self.detail)


class Vote(YearlyData):
    """
    A vote for a nomination by a member. Technically the award field
    is redundant, since the nomination is connected to an award,
    but it's there so that we can enforce uniqueness on it.

    """
    member = models.ForeignKey(Member, related_name='votes')
    award = models.ForeignKey(Award, related_name='votes')
    nomination = models.ForeignKey(Nomination, related_name='votes')

    class Meta:
        unique_together = ('member', 'award', 'year')

    def __unicode__(self):
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

    def __unicode__(self):
        return u"Eligibility result for thread %s in %s: %s" % (self.thread_id if self.post_id is None else u"%s post %s" % (self.thread_id, self.post_id), self.year, self.is_eligible)


class PageViewManager(models.Manager):
    def add_pageview(self, user, page):
        return self.update_or_create(user=user, page=page, defaults={})

    def get_last_pageview(self, user, page):
        pageview = self.filter(user=user, page=page).first() if user.is_authenticated() else None
        return pageview.viewed_time if pageview else timezone.now()


class PageView(models.Model):
    user = models.ForeignKey(User)
    page = models.CharField(max_length=20)
    viewed_time = models.DateTimeField(auto_now=True)

    objects = PageViewManager()

    class Meta:
        unique_together = ('user', 'page')

    def __unicode__(self):
        return u"%s viewed %s at %s" % (self.user, self.page, self.viewed_time)
