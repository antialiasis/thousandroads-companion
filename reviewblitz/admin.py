from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from reviewblitz.models import ReviewBlitzScoring, ReviewBlitz, BlitzReview, BlitzUser, ReviewBlitzTheme, WeeklyTheme

class WeeklyThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

class ThemeInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, instance, **kwargs):
        existing_themes = instance.themes.count() if instance.pk else 0
        return super().__init__(*args, instance=instance, initial=[{'week': n} for n in range(existing_themes + 1, 5)], **kwargs)

class BlitzThemeInline(admin.TabularInline):
    model = ReviewBlitzTheme
    formset = ThemeInlineFormSet
    extra = 4
    max_num = 4

class ReviewBlitzAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date']
    inlines = [BlitzThemeInline]

class BlitzReviewAdmin(admin.ModelAdmin):
    list_display = ['author', 'fic', 'chapters', 'theme', 'approved', 'score', 'edit']
    list_display_links = ['edit']
    list_filter = ['blitz']
    list_select_related = ['review__author', 'review__fic']
    search_fields = ['review__author__username', 'review__fic__title']

    @admin.display(description="Edit")
    def edit(self, obj):
        return "Edit"

    @admin.display(ordering='review__author__username')
    def author(self, obj):
        return obj.review.author

    @admin.display(ordering='review__fic__title')
    def fic(self, obj):
        return obj.review.fic

    @admin.display(ordering='review__chapters')
    def chapters(self, obj):
        return obj.review.chapters

class BlitzUserAdmin(admin.ModelAdmin):
    list_display = ['member', 'blitz', 'bonus_points', 'points_spent']
    list_filter = ['blitz']
    search_fields = ['member']

admin.site.register(ReviewBlitzScoring)
admin.site.register(ReviewBlitz, ReviewBlitzAdmin)
admin.site.register(BlitzReview, BlitzReviewAdmin)
admin.site.register(BlitzUser, BlitzUserAdmin)
admin.site.register(WeeklyTheme, WeeklyThemeAdmin)
