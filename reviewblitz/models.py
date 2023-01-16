from django.db import models
from forum.models import Fic, Member, Review, Chapter


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

    class Meta:
        verbose_name_plural = 'Review blitzes'

    def __str__(self):
        return self.title

    @classmethod
    def get_current(cls):
        return cls.objects.latest("start_date")

    def current_week_index(self):
        delta = datetime.now() - self.start_date
        return int(delta.total_seconds() / (7 * 24 * 60 * 60))


class BlitzReview(models.Model):
    class Meta:
        permissions = (("approve", "Can approve or reject reviews"),)
    blitz = models.ForeignKey(ReviewBlitz, related_name='blitz_reviews', on_delete=models.CASCADE)
    review = models.ForeignKey(Review, related_name='blitz_reviews', on_delete=models.CASCADE)
    theme = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=4, decimal_places=2)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return "{} for {}".format(self.review, self.blitz)

    def week_index(self):
        delta = self.review.posted_date - self.blitz.start_date
        return int(delta.total_seconds() / (7 * 24 * 60 * 60))


class ReviewChapterLink(models.Model):
    review = models.ForeignKey(BlitzReview, related_name='chapter_links', on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, related_name='reviews', on_delete=models.CASCADE)

    def __str__(self):
        return "Chapter: {} reviewed in {}'s review".format(self.chapter, self.review.review.author)


class BlitzUser(models.Model):
    blitz = models.ForeignKey(ReviewBlitz, related_name='blitzes', on_delete=models.CASCADE)
    member = models.ForeignKey(Member, related_name='blitz_members', on_delete=models.CASCADE)
    bonus_points = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    points_spent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return "{}'s stats for {}".format(self.member, self.blitz)
