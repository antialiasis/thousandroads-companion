from django.contrib import admin
from reviewblitz.models import ReviewBlitzScoring, ReviewBlitz, Review, BlitzReview

admin.site.register(ReviewBlitzScoring)
admin.site.register(ReviewBlitz)
admin.site.register(Review)
admin.site.register(BlitzReview)