from django.urls import re_path
from django.views.generic.base import TemplateView, RedirectView
from awards.views import NominationView, NominationLookupView, AllNominationsView, UserNominationsView, AdminNominationView, VotingView, VotingStatsView, ResultsView, PastAwardsView

urlpatterns = [
    re_path(r'^nomination/$', NominationView.as_view(), name='nomination'),
    re_path(r'^nomination/all/(?:(?P<year>\d{4})/)?$', AllNominationsView.as_view(), name='all_nominations'),
    re_path(r'^nomination/(?P<member>\d+)/(?:(?P<year>\d{4})/)?$', UserNominationsView.as_view(), name='user_nominations'),
    re_path(r'^nomination/(?P<member>\d+)/(?:(?P<year>\d{4})/)?edit/$', AdminNominationView.as_view(), name='admin_nomination'),

    re_path(r'^nomination/lookup/fic/$', NominationLookupView.as_view(model=Fic), name='nomination_lookup_fic'),
    re_path(r'^nomination/lookup/member/$', NominationLookupView.as_view(model=Member), name='nomination_lookup_member'),

    re_path(r'^voting/$', VotingView.as_view(), name='voting'),
    re_path(r'^voting/stats/$', VotingStatsView.as_view(), name='voting_stats'),

    re_path(r'^results/(?:(?P<year>\d{4})/)?$', ResultsView.as_view(), name='results'),

    re_path(r'^past_awards/$', PastAwardsView.as_view(), name='past_awards'),
]
