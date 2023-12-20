from django.db.models import Sum, F, Count, Max, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.db import models
from django.utils import timezone
from forum.models import Fic, Member, Review, Chapter


class WeeklyTheme(models.Model):
    name = models.CharField(max_length=50, help_text="A name for this theme, such as 'One-Shot Week'.")
    description = models.TextField(help_text="A basic description of this theme.")
    notes = models.TextField(help_text="A more detailed explanation of what qualifies for this theme.")
    claimable = models.CharField(max_length=11, choices=(('per_chapter', 'Per chapter'), ('per_review', 'Per review'), ('per_fic', 'Per fic')), default='per_fic')
    consecutive_chapter_bonus_applies = models.BooleanField(default=True, help_text="Whether or not the repeat bonus for consecutive chapters, if any, applies when this theme is active.")

    def __str__(self):
        return self.name

    def claimable_theme_bonuses(self, review, prev_reviews):
        if self.claimable == 'per_chapter':
            # We can always claim theme bonus for the number of chapters this review covers
            return review.effective_chapters_reviewed()
        if self.claimable == 'per_review':
            # We can always claim theme bonus once
            return 1
        if self.claimable == 'per_fic':
            # We can claim the theme bonus once if we have not claimed the theme bonus for a review of this fic this week
            week_index = review.week_index()
            return 0 if any(r.week_index() == week_index and r.theme for r in prev_reviews) else 1
        return 0


class ReviewBlitzScoring(models.Model):
    name = models.CharField(max_length=50)
    min_words = models.PositiveIntegerField()
    words_per_chapter = models.PositiveIntegerField()
    chapter_points = models.DecimalField(max_digits=3, decimal_places=2)
    consecutive_chapter_interval = models.PositiveIntegerField()
    consecutive_chapter_bonus = models.DecimalField(max_digits=3, decimal_places=2)
    theme_bonus = models.DecimalField(max_digits=3, decimal_places=2)
    long_chapter_bonus_words = models.PositiveIntegerField()
    long_chapter_bonus = models.DecimalField(max_digits=3, decimal_places=2)

    def __str__(self):
        return self.name


class ReviewBlitz(models.Model):
    title = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    reviews = models.ManyToManyField(Review, through='BlitzReview')
    scoring = models.ForeignKey(ReviewBlitzScoring, related_name='blitzes', on_delete=models.PROTECT)
    themes = models.ManyToManyField(WeeklyTheme, through='ReviewBlitzTheme')

    class Meta:
        verbose_name_plural = 'Review blitzes'

    def __str__(self):
        return self.title

    @classmethod
    def get_current(cls):
        return cls.objects.filter(start_date__lte=timezone.now(), end_date__gt=timezone.now()).latest("start_date")

    def current_week_index(self):
        delta = timezone.now() - self.start_date
        return int(delta.total_seconds() / (7 * 24 * 60 * 60)) + 1

    def get_current_theme(self):
        theme = self.weekly_themes.filter(week=self.current_week_index()).first()
        return theme.theme if theme else None

    def get_leaderboard(self):
        return BlitzReview.objects.filter(blitz=self, approved=True).values('review__author').annotate(points=ExpressionWrapper(Sum('score') + Coalesce(Max('review__author__blitz_members__bonus_points'), 0), output_field=DecimalField()), reviews=Count('review'), chapters=Sum('review__chapters'), words=Sum('review__word_count'), username=F('review__author__username')).order_by('-points')


class ReviewBlitzTheme(models.Model):
    blitz = models.ForeignKey(ReviewBlitz, on_delete=models.CASCADE, related_name='weekly_themes')
    theme = models.ForeignKey(WeeklyTheme, on_delete=models.CASCADE)
    week = models.PositiveIntegerField()

    class Meta:
        ordering = ['week']

    def __str__(self):
        return "{} week {}: {}".format(self.blitz, self.week, self.theme)


class BlitzReview(models.Model):
    class Meta:
        permissions = (("approve", "Can approve or reject reviews"),)
    blitz = models.ForeignKey(ReviewBlitz, related_name='blitz_reviews', on_delete=models.CASCADE)
    review = models.ForeignKey(Review, related_name='blitz_reviews', on_delete=models.CASCADE)
    theme = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=4, decimal_places=2)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return str(self.review)

    def week_index(self):
        delta = self.review.posted_date - self.blitz.start_date
        return int(delta.total_seconds() / (7 * 24 * 60 * 60)) + 1

    def get_theme(self):
        theme = self.blitz.weekly_themes.filter(week=self.week_index()).first()
        return theme.theme if theme else None

    def effective_chapters_reviewed(self):
        return min(self.review.word_count // self.blitz.scoring.words_per_chapter, self.review.chapters)


class ReviewChapterLink(models.Model):
    review = models.ForeignKey(BlitzReview, related_name='chapter_links', on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, related_name='reviews', on_delete=models.CASCADE)

    class Meta:
        ordering: ["chapter__post_id"]

    def __str__(self):
        return "Chapter: {} reviewed in {}'s review".format(self.chapter, self.review.review.author)


class BlitzUser(models.Model):
    blitz = models.ForeignKey(ReviewBlitz, related_name='blitzes', on_delete=models.CASCADE)
    member = models.ForeignKey(Member, related_name='blitz_members', on_delete=models.CASCADE)
    bonus_points = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    points_spent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return "{}'s stats for {}".format(self.member, self.blitz)
