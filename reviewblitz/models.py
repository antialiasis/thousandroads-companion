from django.db import models
from forum.models import Fic, Member


class ReviewBlitzScoring(models.Model):
    name = models.CharField(max_length=50)
    min_words = models.PositiveIntegerField()
    words_per_chapter = models.PositiveIntegerField()
    chapter_points = models.DecimalField(max_digits=3, decimal_places=2)
    consecutive_chapter_interval = models.PositiveIntegerField()
    consecutive_chapter_bonus = models.DecimalField(max_digits=3, decimal_places=2)
    theme_bonus = models.DecimalField(max_digits=3, decimal_places=2)

    def __str__(self):
        return self.name


class ReviewBlitz(models.Model):
    title = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    reviews = models.ManyToManyField('Review', through='BlitzReview')
    scoring = models.ForeignKey(ReviewBlitzScoring, related_name='blitzes', on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = 'Review blitzes'

    def __str__(self):
        return self.title


class Review(models.Model):
    post_id = models.PositiveIntegerField(unique=True, primary_key=True)
    author = models.ForeignKey(Member, related_name='reviews', on_delete=models.PROTECT)
    fic = models.ForeignKey(Fic, related_name='reviews', on_delete=models.PROTECT)
    posted_date = models.DateTimeField()
    word_count = models.PositiveIntegerField()
    chapters = models.PositiveIntegerField(default=1)
    blitzes = models.ManyToManyField(ReviewBlitz, through='BlitzReview')

    def __str__(self):
        return "{}'s review on {}".format(self.author, self.fic.title)


class BlitzReview(models.Model):
    class Meta:
        permissions = (("approve", "Can approve or reject reviews"),)
    blitz = models.ForeignKey(ReviewBlitz, related_name='blitz_reviews', on_delete=models.CASCADE)
    review = models.ForeignKey(Review, related_name='blitz_reviews', on_delete=models.CASCADE)
    theme = models.BooleanField(default=False)
    score = models.PositiveIntegerField()
    approved = models.BooleanField(default=False)

    def __str__(self):
        return "{} for {}".format(self.review, self.blitz)
