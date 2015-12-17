from django.conf import settings
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from extra_views.formsets import FormSetView
from awards.forms import YearAwardForm, BaseYearAwardFormSet, NominationForm, BaseNominationFormSet, VotingForm
from awards.models import YearAward
from serebii.models import Member, Fic
from serebii.forms import TempUserProfileForm


def awards_context(request):
    return {
        'year': settings.YEAR,
        'phase': settings.PHASE,
        'min_year': settings.MIN_YEAR,
        'max_year': settings.MAX_YEAR,
        'max_fic_nominations': settings.MAX_FIC_NOMINATIONS,
        'max_person_nominations': settings.MAX_PERSON_NOMINATIONS,
        'min_different_nominations': settings.MIN_DIFFERENT_NOMINATIONS
    }


class LoginRequiredMixin(object):
    """
    A mixin to make views require login.

    """
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class YearAwardsMassEditView(FormSetView):
    form_class = YearAwardForm
    formset_class = BaseYearAwardFormSet
    extra = 0
    success_url = reverse_lazy('admin:awards_yearaward_changelist')
    template_name = "admin/awards/set_yearawards.html"
    extra_context = {}

    def get_valid_year(self, year):
        try:
            year = int(year)
        except ValueError:
            year = settings.YEAR
        year = max(year, settings.MIN_YEAR)
        year = min(year, settings.MAX_YEAR)
        return year

    def get(self, *args, **kwargs):
        if not kwargs['year'] and 'year' in self.request.GET:
            return HttpResponseRedirect(reverse('admin:set_year_awards', kwargs={'year': self.get_valid_year(self.request.GET['year'])}))
        elif kwargs['year'] != str(self.get_valid_year(kwargs['year'])):
            return HttpResponseRedirect(reverse('admin:set_year_awards', kwargs={'year': self.get_valid_year(kwargs['year'])}))
        return super(YearAwardsMassEditView, self).get(*args, **kwargs)

    def get_formset_kwargs(self):
        kwargs = super(YearAwardsMassEditView, self).get_formset_kwargs()
        kwargs['year'] = self.get_valid_year(self.kwargs['year'])
        return kwargs

    def formset_valid(self, formset):
        formset.save()
        return super(YearAwardsMassEditView, self).formset_valid(formset)

    def get_context_data(self, **kwargs):
        context = super(YearAwardsMassEditView, self).get_context_data(**kwargs)
        context['opts'] = YearAward._meta
        context['title'] = u"Set awards for %s" % self.get_valid_year(self.kwargs['year'])
        context['year_editing'] = self.get_valid_year(self.kwargs['year'])
        context['app_label'] = 'awards'
        context.update(**self.extra_context)
        return context


class TempUserMixin(object):
    def get_context_data(self, **kwargs):
        if not self.request.user.is_authenticated():
            return { 'form': kwargs.get('form', TempUserProfileForm()) }
        else:
            return super(TempUserMixin, self).get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            return super(TempUserMixin, self).post(*args, **kwargs)
        else:
            form = TempUserProfileForm(data=self.request.POST)
            if form.is_valid():
                user = form.create_temp_user()
                login(self.request, user)
                messages.success(self.request, mark_safe(u'You have now been logged in as a temporary user. %s' % self.temp_user_success_message))
                return HttpResponseRedirect(self.get_success_url())
            else:
                return self.render_to_response(self.get_context_data(form=form))

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            return super(TempUserMixin, self).get(*args, **kwargs)
        else:
            form = TempUserProfileForm()
            return self.render_to_response(self.get_context_data(form=form))


class NominationView(TempUserMixin, FormSetView):
    form_class = NominationForm
    formset_class = BaseNominationFormSet
    extra = 0
    success_url = reverse_lazy('nomination')
    template_name = "nomination.html"
    temp_user_success_message = 'After making your nominations, you <strong>must</strong> post in <a href="%s">the nomination thread on the forums</a> to confirm your identity.' % settings.NOMINATION_THREAD

    def get_formset_kwargs(self):
        kwargs = super(NominationView, self).get_formset_kwargs()
        kwargs['year'] = settings.YEAR
        kwargs['member'] = self.request.user.member
        return kwargs

    def formset_valid(self, formset):
        formset.save()
        msg = "You may return here at any point until the end of the nomination phase to change your nominations." if self.request.user.verified else 'Remember, in order for your nominations to be counted you must <strong>post in <a href="%s">the nomination thread</a></strong> to confirm that this is you!' % settings.NOMINATION_THREAD
        messages.success(self.request, mark_safe(u"Your nominations have been saved. %s" % msg))
        return super(NominationView, self).formset_valid(formset)

    def get_context_data(self, **kwargs):
        context = super(NominationView, self).get_context_data(**kwargs)
        context['all_fics'] = Fic.objects.prefetch_related('authors')
        context['all_authors'] = Member.objects.all()
        return context


class AllNominationsView(ListView):
    context_object_name = 'year_awards'
    template_name = "all_nominations.html"

    def get_queryset(self):
        return YearAward.objects.get_with_distinct_nominations()

    def get_context_data(self, **kwargs):
        context = super(AllNominationsView, self).get_context_data(**kwargs)
        verified_filter = Q(user__isnull=True) | Q(user__verified=True)
        context['nominators'] = Member.objects.filter(verified_filter, nominations_by__year=settings.YEAR).values_list('username', flat=True).distinct()
        context['unverified_nominators'] = Member.objects.filter(nominations_by__year=settings.YEAR).exclude(verified_filter).values_list('username', flat=True).distinct()
        return context


class AdminNominationView(NominationView):
    """
    A view to let admins submit nominations as other users.

    """
    def get_success_url(self):
        return reverse('admin_nomination', kwargs={'member': self.kwargs['member']})

    def get_formset_kwargs(self):
        kwargs = super(NominationView, self).get_formset_kwargs()
        kwargs['year'] = self.kwargs.get('year') or settings.YEAR
        kwargs['member'] = Member.from_params(user_id=self.kwargs['member'], save=True)
        return kwargs

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_staff:
            raise PermissionDenied
        return super(AdminNominationView, self).dispatch(*args, **kwargs)


class VotingView(TempUserMixin, FormView):
    form_class = VotingForm
    template_name = "voting.html"
    success_url = reverse_lazy('voting')
    temp_user_success_message = 'After placing your votes, you <strong>must</strong> post in <a href="%s">the voting thread on the forums</a> to confirm your identity.' % settings.VOTING_THREAD

    def get_form_kwargs(self):
        kwargs = super(VotingView, self).get_form_kwargs()
        kwargs['year'] = settings.YEAR
        kwargs['member'] = self.request.user.member
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(VotingView, self).get_context_data(**kwargs)
        context['year_awards'] = YearAward.objects.get_with_distinct_nominations()
        return context

    def form_valid(self, form):
        form.save()
        msg = "You may return here at any point until the end of the voting phase to change your votes." if self.request.user.verified else 'Remember, in order for your votes to be counted you must <strong>post in <a href="%s">the voting thread</a></strong> to confirm that this is you!' % settings.VOTING_THREAD
        messages.success(self.request, mark_safe(u"Your votes have been saved. %s Thank you for participating!" % msg))
        return super(VotingView, self).form_valid(form)


class VotingStatsView(ListView):
    """
    A view that lets admins view voting results.

    """
    context_object_name = 'year_awards'
    template_name = 'voting_stats.html'

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_staff:
            raise PermissionDenied
        return super(VotingStatsView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        awards = YearAward.objects.get_with_distinct_nominations(with_votes=True)
        for award in awards:
            for i, nomination in enumerate(award.distinct_nominations):
                num_votes = nomination.get_votes()
                high_place = i
                low_place = i
                while high_place > 0 and award.distinct_nominations[high_place - 1].get_votes() == num_votes:
                    high_place -= 1
                while low_place < len(award.distinct_nominations) - 1 and award.distinct_nominations[low_place + 1].get_votes() == num_votes:
                    low_place += 1
                nomination.place = [high_place + 1, low_place + 1]
        return awards

    def get_context_data(self, **kwargs):
        context = super(VotingStatsView, self).get_context_data(**kwargs)
        verified_filter = Q(user__isnull=True) | Q(user__verified=True)
        context['voters'] = Member.objects.filter(verified_filter, votes__year=settings.YEAR).values_list('username', flat=True).distinct()
        context['unverified_voters'] = Member.objects.filter(votes__year=settings.YEAR).exclude(verified_filter).values_list('username', flat=True).distinct()
        return context