import json
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView, CreateView, UpdateView
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from serebii.models import User, Member, Fic
from serebii.forms import VerificationForm, RegisterForm, UserInfoForm, UserLookupForm, PasswordResetForm


class JSONViewMixin(object):
    """
    Add to a form view to enable AJAX JSON responses.

    """
    def render_to_json_response(self, context, **response_kwargs):
        data = json.dumps(context)
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)


class RegisterView(CreateView):
    template_name = "register.html"
    form_class = RegisterForm
    success_url = reverse_lazy('verification')

    def form_valid(self, form):
        response = super(RegisterView, self).form_valid(form)
        user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password1'])
        login(self.request, user)
        return response


class EditUserInfoView(UpdateView):
    template_name = "edit_user_info.html"
    model = User
    form_class = UserInfoForm
    success_url = reverse_lazy('edit_user_info')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, u"Your information has been successfully edited!")
        return super(EditUserInfoView, self).form_valid(form)


class VerificationView(FormView):
    template_name = "verification.html"
    form_class = VerificationForm
    success_url = reverse_lazy('home')

    def get_form_kwargs(self):
        kwargs = super(VerificationView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.request.user.member = form.member
        self.request.user.verified = True
        self.request.user.save()
        messages.success(self.request, u"You have been successfully verified as %s! You can change your Biography profile field on the forums back now, if you like." % form.member)
        return super(VerificationView, self).form_valid(form)


class PasswordResetLookupView(FormView):
    template_name = "password_reset_lookup.html"
    form_class = UserLookupForm

    def get_success_url(self):
        return reverse('reset_password', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        self.object = form.user
        self.object.verification_code = User.objects.make_random_password()
        self.object.save()
        return super(PasswordResetLookupView, self).form_valid(form)


class PasswordResetView(SingleObjectMixin, FormView):
    model = User
    template_name = "password_reset.html"
    form_class = PasswordResetForm
    success_url = reverse_lazy('home')
    context_object_name = 'reset_user'

    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        return super(PasswordResetView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        return User.objects.filter(verified=True, member__isnull=False)

    def get_form_kwargs(self):
        kwargs = super(PasswordResetView, self).get_form_kwargs()
        kwargs['user'] = self.object
        return kwargs

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, u"Your password has been successfully reset! You can change your Biography profile field on the forums back now, if you like.")
        response = super(PasswordResetView, self).form_valid(form)
        user = authenticate(username=user.username, password=form.cleaned_data['password1'])
        login(self.request, user)
        return response


class SerebiiObjectLookupView(JSONViewMixin, View):
    model = None

    def get_page(self):
        try:
            url = self.request.GET['url']
        except KeyError:
            return None

        page_class = self.model.get_page_class()

        try:
            params = page_class.get_params_from_url(url)
        except ValueError:
            return None
        if self.model == Fic and self.request.GET.get('type', 'thread') == 'thread':
            params['post_id'] = None
        return page_class.from_params(save=True, **params)

    def get(self, *args, **kwargs):
        try:
            page = self.get_page()
        except ValidationError as e:
            context = {'error': e.message}
        else:
            obj = page.object
            if isinstance(obj, Fic):
                other_objects = [author.to_dict() for author in obj.authors.all()]
            else:
                other_objects = []

            if obj is None:
                context = {'error': u"Lookup failed. Please double-check that you entered a valid URL."}
            else:
                context = obj.to_dict()
                context['other_objects'] = other_objects
        return self.render_to_json_response(context)
