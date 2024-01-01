from django.urls import reverse_lazy, re_path
from django.views.generic.base import TemplateView, RedirectView
from django.contrib.auth.views import LoginView, LogoutView
from forum.views import VerificationView, RegisterView, EditUserInfoView, ForumObjectLookupView, PasswordResetLookupView, PasswordResetView, CatalogView, CatalogAuthorView, CatalogFicView, CatalogSearchView, CatalogGenreView, CatalogTagView
from reviewblitz.views import BlitzReviewSubmissionFormView, BlitzReviewApprovalQueueView, BlitzLeaderboardView, BlitzUserView, BlitzHistoryView, BlitzView, HasReviewedView
from forum.models import Member, Fic, Chapter

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # Examples:
    re_path(r'^$', RedirectView.as_view(url='blitz/leaderboard'), name='home'),
    re_path(r'^catalog/$', CatalogView.as_view(), name='catalog'),
    re_path(r'^catalog/author/(?P<member>\d+)/$', CatalogAuthorView.as_view(), name='catalog_author'),
    re_path(r'^catalog/fic/(?P<pk>\d+)/$', CatalogFicView.as_view(), name='catalog_fic'),
    re_path(r'^catalog/search/$', CatalogSearchView.as_view(), name='catalog_search'),
    re_path(r'^catalog/genre/(?P<slug>[\w-]+)/$', CatalogGenreView.as_view(), name='catalog_genre'),
    re_path(r'^catalog/tag/(?P<tag>[\w-]+)/$', CatalogTagView.as_view(), name='catalog_tag'),
    re_path(r'^login/$', LoginView.as_view(template_name='login.html'), name='login'),
    re_path(r'^reset_password/$', PasswordResetLookupView.as_view(), name='reset_password'),
    re_path(r'^reset_password/user/(?P<pk>\d+)/$', PasswordResetView.as_view(), name='reset_password'),
    re_path(r'^logout/$', LogoutView.as_view(next_page=reverse_lazy('home')), name='logout'),
    re_path(r'^register/$', RegisterView.as_view(), name='register'),
    re_path(r'^user_info/$', EditUserInfoView.as_view(), name='edit_user_info'),
    re_path(r'^verify/$', VerificationView.as_view(), name='verification'),

    re_path(r'^lookup/fic/$', ForumObjectLookupView.as_view(model=Fic), name='lookup_fic'),
    re_path(r'^lookup/member/$', ForumObjectLookupView.as_view(model=Member), name='lookup_member'),
    re_path(r'^lookup/chapter/$', ForumObjectLookupView.as_view(model=Chapter), name='lookup_chapter'),

    re_path(r'^blitz/history/$', BlitzHistoryView.as_view(), name="blitz_history"),
    re_path(r'^blitz/submit/$', BlitzReviewSubmissionFormView.as_view(), name="blitz_review_submit"),
    re_path(r'^blitz/queue/$', BlitzReviewApprovalQueueView.as_view(), name="blitz_review_approval_queue"),
    re_path(r'^blitz/leaderboard/$', BlitzLeaderboardView.as_view(), name="blitz_leaderboard"),
    re_path(r'^blitz/has_reviewed/$', HasReviewedView.as_view(), name="has_reviewed"),
    re_path(r'^blitz/user/$', BlitzUserView.as_view(), name="blitz_user"),
    re_path(r'^blitz/(?P<pk>\d+)/$', BlitzView.as_view(), name="blitz"),

    re_path(r'^admin/', admin.site.urls),
]
