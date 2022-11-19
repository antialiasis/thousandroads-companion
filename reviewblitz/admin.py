from django.contrib import admin
from reviewblitz.models import ReviewBlitzScoring, ReviewBlitz, BlitzReview

admin.site.register(ReviewBlitzScoring)
admin.site.register(ReviewBlitz)
admin.site.register(BlitzReview)