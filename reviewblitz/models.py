import decimal
from django.db.models import Sum, F, Count, Max, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.db import models
from django.utils import timezone
from forum.models import Fic, Member, Review, Chapter


class WeeklyTheme(models.Model):
    name = models.CharField(max_length=50, help_text="A name for this theme, such as 'One-Shot Week'.")
    description = models.TextField(help_text="A basic description of this theme.")
    notes = models.TextField(help_text="A more detailed explanation of what qualifies for this theme.")
    claimable = models.CharField(max_length=11, choices=(('per_chapter', 'Per chapter'), ('per_review', 'Per review'), ('per_fic', 'Per fic')), default='per_fic', help_text="Per chapter means the bonus can be claimed once per chapter covered by a review. Per review means it can be claimed only once per review, though it could be claimed multiple times per fic in separate reviews. Per fic means it can be claimed once per fic for this week.")
    subsequent_chapter_theme_bonus = models.BooleanField(default=False, help_text="Check this box to automatically apply the theme bonus to all chapters after the first in multi-chapter reviews (only relevant if the theme is claimable per chapter). This would be appropriate if the theme is something like 'Any chapterfic' or 'Any story you've already reviewed before'. If not checked for a per-chapter theme, the theme bonus will be applied for all the chapters if the box is checked or no chapters otherwise.")
    consecutive_chapter_bonus_applies = models.BooleanField(default=True, help_text="Whether or not the repeat bonus for consecutive chapters, if any, applies when this theme is active.")

    def __str__(self):
        return self.name

    def claimable_theme_bonuses(self, theme_box_checked, review, prev_reviews):
        if self.claimable == 'per_chapter':
            # If this theme automatically applies theme bonus to subsequent chapters,
            # then we want the theme box to determine whether we get a bonus for the
            # first chapter while always giving a bonus for the rest.
            # Otherwise, we get a bonus for every chapter reviewed if the box is checked.
            chapters = review.effective_chapters_reviewed()
            return theme_box_checked + chapters - 1 if self.subsequent_chapter_theme_bonus else chapters * theme_box_checked
        if self.claimable == 'per_review':
            # We can always claim theme bonus once.
            return 1 * theme_box_checked
        if self.claimable == 'per_fic':
            # We can claim the theme bonus once if we have not claimed the theme bonus for a review of this fic this week.
            week_index = review.week_index()
            return 0 if any(r.week_index() == week_index and r.theme for r in prev_reviews) else 1 * theme_box_checked
        return 0


class ReviewBlitzScoring(models.Model):
    name = models.CharField(max_length=50)
    min_words = models.PositiveIntegerField(verbose_name="Minimum words for review", help_text="The minimum number of words a review must be to be counted.")
    words_per_chapter = models.PositiveIntegerField(help_text="The number of words per chapter to make a review count for full points for each chapter.")
    chapter_points = models.DecimalField(max_digits=3, decimal_places=2, help_text="The number of points given for each chapter.")
    consecutive_chapter_interval = models.PositiveIntegerField(help_text="The number of chapters that must be reviewed to earn the consecutive chapter bonus (if enabled for the weekly theme).")
    consecutive_chapter_bonus = models.DecimalField(max_digits=3, decimal_places=2, help_text="The bonus points given for each (consecutive chapter interval) number of chapters reviewed of the same fic.")
    theme_bonus = models.DecimalField(max_digits=3, decimal_places=2, help_text="The bonus given for a review that adheres to the weekly theme.")
    long_chapter_bonus_words = models.PositiveIntegerField(help_text="The word count threshold above which a long chapter bonus can be given.")
    long_chapter_bonus = models.DecimalField(max_digits=3, decimal_places=2, help_text="The bonus points given for reviewing a long chapter.")
    heat_bonus_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=0, help_text="The multiplier applied to the ratio of (reviews given + 1) / (reviews received + 1) to determine the heat bonus. (Set to 0 to disable this bonus.)")
    max_heat_bonus = models.DecimalField(max_digits=3, decimal_places=2, default=0, help_text="The maximum heat bonus that can be given.")

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
        return cls.objects.latest("start_date")

    def is_active(self):
        return self.start_date <= timezone.now() and self.end_date > timezone.now()

    def current_week_index(self):
        delta = timezone.now() - self.start_date
        return int(delta.total_seconds() / (7 * 24 * 60 * 60)) + 1

    def get_current_theme(self):
        theme = self.weekly_themes.filter(week=self.current_week_index()).first()
        return theme.theme if theme else None

    def get_leaderboard(self):
        return BlitzUser.objects.raw("""
            SELECT
                s.id,
                s.username,
                s.points,
                s.reviews,
                s.chapters,
                s.words,
                s.chapters_received,
                (CASE
                    WHEN s.base_heat_bonus < 0 THEN 0
                    WHEN s.base_heat_bonus > %(max_heat_bonus)s THEN %(max_heat_bonus)s
                    ELSE ROUND(s.base_heat_bonus * 2) / 2
                END) AS heat_bonus
            FROM (
                SELECT
                    blitz_user.id,
                    member.username,
                    SUM(blitz_review.score) + COALESCE(blitz_user.bonus_points, 0) AS points,
                    COUNT(blitz_review.id) AS reviews,
                    SUM(review.chapters) AS chapters,
                    SUM(review.word_count) AS words,
                    COALESCE(received_reviews.chapters_received, 0) AS chapters_received,
                    COALESCE(((SUM(review.chapters) + 1) / (COALESCE(received_reviews.chapters_received, 0) + 1)) * %(heat_bonus_multiplier)s - 1, 0) AS base_heat_bonus
                FROM reviewblitz_blitzuser AS blitz_user
                    INNER JOIN forum_member AS member
                        ON blitz_user.member_id = member.user_id
                    LEFT JOIN forum_review AS review
                        ON review.author_id = member.user_id
                    LEFT JOIN reviewblitz_blitzreview AS blitz_review
                        ON blitz_review.review_id = review.post_id
                        AND blitz_review.blitz_id = blitz_user.blitz_id
                    LEFT JOIN (
                        SELECT
                            authors.member_id,
                            SUM(CASE WHEN ROUND(received_review.word_count / %(words_per_chapter)s) < received_review.chapters THEN CAST(ROUND(received_review.word_count / %(words_per_chapter)s) AS INT) ELSE received_review.chapters END) AS chapters_received
                        FROM forum_review AS received_review
                            INNER JOIN reviewblitz_blitzreview AS received_blitzreview
                                ON received_blitzreview.review_id = received_review.post_id
                                AND received_blitzreview.blitz_id = %(blitz_id)s
                                AND received_blitzreview.approved
                            INNER JOIN forum_fic AS fic
                                ON received_review.fic_id = fic.id
                            INNER JOIN forum_fic_authors AS authors
                                ON authors.fic_id = fic.id
                        GROUP BY authors.member_id
                    ) AS received_reviews
                        ON received_reviews.member_id = member.user_id
                WHERE blitz_user.blitz_id = %(blitz_id)s
                    AND blitz_review.approved
                GROUP BY blitz_user.id, member.user_id, received_reviews.member_id
                ORDER BY points DESC
            ) s
        """, dict(
            blitz_id=self.id,
            words_per_chapter=self.scoring.words_per_chapter,
            max_heat_bonus=float(self.scoring.max_heat_bonus),
            heat_bonus_multiplier=float(self.scoring.heat_bonus_multiplier)
        ))


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
    heat_bonus = models.DecimalField(max_digits=2, decimal_places=1, default=0)

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

    def calculate_heat_bonus(self):
        heat_bonus = 0
        # If hypothetically a fic has mutliple authors, we should get the biggest heat bonus that applies for any of them.
        for author in self.review.fic.get_authors():
            try:
                recipient = BlitzUser.objects.get(blitz=self.blitz, member=author)
            except BlitzUser.DoesNotExist:
                # This author is not participating in Blitz - no heat bonus.
                return 0

            # Have we already claimed a heat bonus for this author this Blitz?
            prev_heat_bonus = BlitzReview.objects.filter(blitz=self.blitz, review__author=self.review.author, review__fic__authors=author, heat_bonus__gt=0).exists()

            if prev_heat_bonus:
                # We've already received a heat bonus for this author this Blitz - no double-dipping.
                continue

            reviews_given = BlitzReview.objects.filter(blitz=self.blitz, review__author=author).count()
            reviews_received = BlitzReview.objects.filter(blitz=self.blitz, review__fic__authors=author).count()

            if reviews_given <= reviews_received:
                # No bonus for an author who has received the same number or more reviews than they've given.
                continue

            base_bonus = min((reviews_given + 1) / (reviews_received + 1) * float(self.blitz.scoring.heat_bonus_multiplier) - 1, float(self.blitz.scoring.max_heat_bonus))

            # Round to the nearest half-point.
            rounded_bonus = int(base_bonus * 2 + 0.5) / 2

            # If this is bigger than the heat bonus we currently have, replace it.
            if rounded_bonus > heat_bonus:
                heat_bonus = rounded_bonus

        return decimal.Decimal(heat_bonus)


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
