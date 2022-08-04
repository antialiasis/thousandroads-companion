from django.conf.urls import url
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from serebii.views import VerificationView, RegisterView, EditUserInfoView, SerebiiObjectLookupView, PasswordResetLookupView, PasswordResetView, CatalogView, CatalogAuthorView, CatalogFicView, CatalogSearchView, CatalogGenreView, CatalogTagView
from awards.views import NominationView, NominationLookupView, AllNominationsView, UserNominationsView, AdminNominationView, VotingView, VotingStatsView, ResultsView, PastAwardsView
from serebii.models import Member, Fic

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # Examples:
    url(r'^$', TemplateView.as_view(template_name='home.html'), name='home'),
    url(r'^catalog/$', CatalogView.as_view(), name='catalog'),
    url(r'^catalog/author/(?P<member>\d+)/$', CatalogAuthorView.as_view(), name='catalog_author'),
    url(r'^catalog/fic/(?P<pk>\d+)/$', CatalogFicView.as_view(), name='catalog_fic'),
    url(r'^catalog/search/$', CatalogSearchView.as_view(), name='catalog_search'),
    url(r'^catalog/genre/(?P<slug>[\w-]+)/$', CatalogGenreView.as_view(), name='catalog_genre'),
    url(r'^catalog/tag/(?P<tag>[\w-]+)/$', CatalogTagView.as_view(), name='catalog_tag'),
    url(r'^login/$', LoginView.as_view(template_name='login.html'), name='login'),
    url(r'^reset_password/$', PasswordResetLookupView.as_view(), name='reset_password'),
    url(r'^reset_password/user/(?P<pk>\d+)/$', PasswordResetView.as_view(), name='reset_password'),
    url(r'^logout/$', LogoutView.as_view(next_page=reverse_lazy('home')), name='logout'),
    url(r'^register/$', RegisterView.as_view(), name='register'),
    url(r'^user_info/$', EditUserInfoView.as_view(), name='edit_user_info'),
    url(r'^verify/$', VerificationView.as_view(), name='verification'),

    url(r'^lookup/fic/$', SerebiiObjectLookupView.as_view(model=Fic), name='lookup_fic'),
    url(r'^lookup/member/$', SerebiiObjectLookupView.as_view(model=Member), name='lookup_member'),

    url(r'^nomination/$', NominationView.as_view(), name='nomination'),
    url(r'^nomination/all/(?:(?P<year>\d{4})/)?$', AllNominationsView.as_view(), name='all_nominations'),
    url(r'^nomination/(?P<member>\d+)/(?:(?P<year>\d{4})/)?$', UserNominationsView.as_view(), name='user_nominations'),
    url(r'^nomination/(?P<member>\d+)/(?:(?P<year>\d{4})/)?edit/$', AdminNominationView.as_view(), name='admin_nomination'),

    url(r'^nomination/lookup/fic/$', NominationLookupView.as_view(model=Fic), name='nomination_lookup_fic'),
    url(r'^nomination/lookup/member/$', NominationLookupView.as_view(model=Member), name='nomination_lookup_member'),

    url(r'^voting/$', VotingView.as_view(), name='voting'),
    url(r'^voting/stats/$', VotingStatsView.as_view(), name='voting_stats'),

    url(r'^results/(?:(?P<year>\d{4})/)?$', ResultsView.as_view(), name='results'),

    url(r'^past_awards/$', PastAwardsView.as_view(), name='past_awards'),

    url(r'^admin/', admin.site.urls),
]
