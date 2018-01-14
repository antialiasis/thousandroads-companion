from django.contrib import admin
from django.conf.urls import patterns, url
from awards.models import Category, Award, YearAward, Nomination, FicEligibility
from awards.views import YearAwardsMassEditView


class YearAwardsAdmin(admin.ModelAdmin):
    fields = ('year', 'award')
    list_display = ('year', 'award')
    list_filter = ('year',)
    list_select_related = ('award',)

    def __init__(self, *args, **kwargs):
        super(YearAwardsAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None,)

    def get_urls(self):
        urls = super(YearAwardsAdmin, self).get_urls()

        return patterns('',
            url(r'^set_year_awards/(?:(?P<year>\d+)/)?$', self.admin_site.admin_view(YearAwardsMassEditView.as_view(extra_context={'current_app': self.admin_site.name})), name='set_year_awards')
        ) + urls


class AwardAdmin(admin.ModelAdmin):
    list_display = ('category', 'name', 'display_order')
    list_display_links = ('name',)
    list_editable = ('display_order',)
    list_select_related = ('category',)


class NominationAdmin(admin.ModelAdmin):
    list_display = ('award', 'nomination_text', 'member')
    list_display_links = ('nomination_text',)
    list_select_related = ('fic', 'nominee', 'member', 'award')
    list_filter = ('year',)
    search_fields = ('member__username', 'award__name', 'fic__title')
    ordering = ['-year', 'award']


admin.site.register(Category)
admin.site.register(Award, AwardAdmin)
admin.site.register(YearAward, YearAwardsAdmin)
admin.site.register(FicEligibility)
admin.site.register(Nomination, NominationAdmin)
