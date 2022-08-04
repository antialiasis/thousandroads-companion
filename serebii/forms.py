import re
import requests
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.html import format_html, mark_safe
from django.utils.text import slugify
from serebii.models import Member, User, MemberPage, Fic
from awards.models import Phase


class SerebiiLinkField(forms.CharField):
    """
    A field for a link to a SerebiiPage.

    """
    empty_values = [None]

    def __init__(self, page_class, *args, **kwargs):
        self.page_class = page_class
        self.force_download = kwargs.pop('force_download', False)
        super(SerebiiLinkField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(SerebiiLinkField, self).to_python(value)
        if not value:
            return None
        try:
            value = self.page_class.from_url(value, self.force_download)
        except ValueError:
            raise ValidationError(u"Invalid %s URL. Please ensure that you have entered the full URL including the https:// portion." % self.page_class.__name__, code='invalid')
        return value

    def prepare_value(self, value):
        if not isinstance(value, self.page_class):
            return ''
        return value.get_url()


class CatalogSearchForm(forms.Form):
    query = forms.CharField()

    def get_results(self):
        if self.is_valid():
            query = self.cleaned_data['query']
            return Fic.objects.filter(Q(tags__tag__icontains=query) | Q(title__icontains=query) | Q(summary__icontains=query))
        return []


class CatalogFicForm(forms.ModelForm):
    tags = forms.CharField()

    class Meta:
        model = Fic
        fields = ('summary', 'genres', 'completed')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tags'].initial = ', '.join([tag.tag for tag in self.instance.tags.all()])

    def clean_tags(self):
        return [slugify(tag) for tag in self.cleaned_data['tags'].split(',')]

    def save(self, commit=True):
        self.instance._tags = self.cleaned_data['tags']
        return super().save(commit)



class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username',)


class UserLookupForm(forms.Form):
    """
    A form for looking up a verified user by username, for the reset
    password feature.

    """
    username = forms.CharField()

    def clean(self):
        try:
            user = User.objects.get(username=self.cleaned_data['username'])
        except User.DoesNotExist:
            raise ValidationError(u"There is no user with this username. You should probably just register a new account.")
        if not user.verified or user.member is None:
            raise ValidationError(u"This user has not connected a Serebii account and therefore cannot be verified. You should probably register a new account.")
        self.user = user
        return self.cleaned_data


class PasswordResetForm(forms.Form):
    """
    A password reset form that verifies a verification code on the
    user's Serebii profile page rather than sending e-mails.

    """
    password1 = forms.CharField(label=u"New password", widget=forms.PasswordInput)
    password2 = forms.CharField(label=u"Confirm password", widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(PasswordResetForm, self).__init__(*args, **kwargs)

    def clean(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(u"The two password fields didn't match.")

        member_page = MemberPage.from_url(self.user.member.link(), True)
        self.user.validate_verification_code(member_page)
        return self.cleaned_data

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['password1'])
        if commit:
            self.user.save()
        return self.user


class UserInfoForm(forms.ModelForm):
    """
    A form to edit a user's username and password.

    """
    password1 = forms.CharField(label=u"New password", widget=forms.PasswordInput)
    password2 = forms.CharField(label=u"Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username',)

    def clean(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(u"The two password fields didn't match.")

        return self.cleaned_data

    def save(self, commit=True):
        user = super(UserInfoForm, self).save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class VerificationForm(forms.Form):
    """
    A form for verifying a user through a verification code on a
    profile page.

    """
    profile_url = SerebiiLinkField(MemberPage, label=u"Profile URL", help_text=u"Please enter your full Serebii.net forums profile URL, e.g. https://forums.serebii.net/members/dragonfree.388/", force_download=True)
    verify_current = forms.BooleanField(required=False, label=u"Verify existing nominations/votes?", help_text=mark_safe(u"This member has already submitted unverified nominations/votes. To verify them now, check this box. <strong>Do not check this box unless you are certain that you submitted these nominations/votes!</strong> You can verify them later by resubmitting them."))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.made_unverified = kwargs.pop('has_unverified', False)
        super(VerificationForm, self).__init__(*args, **kwargs)
        has_unverified = False
        if user.member:
            del self.fields['profile_url']
            if not self.made_unverified:
                phase = Phase.get_current()
                if phase == 'nomination':
                    has_unverified = user.member.nominations_by.from_year().filter(verified=False).exists()
                elif phase == 'voting':
                    has_unverified = user.member.votes.from_year().filter(verified=False).exists()
        if not has_unverified:
            del self.fields['verify_current']

    def clean(self):
        if self.user.member:
            profile_page = MemberPage.from_url(self.user.member.link(), True)
        elif 'profile_url' in self.cleaned_data:
            profile_page = self.cleaned_data['profile_url']
        else:
            raise ValidationError(u"You must provide a profile URL.")
        self.user.validate_verification_code(profile_page)
        self.member = profile_page.object
        self.member.save()
        return self.cleaned_data


class TempUserProfileForm(forms.Form):
    """
    A form that creates a temporary user account from the given profile link.

    """
    profile_url = SerebiiLinkField(MemberPage, label=u"Profile URL", help_text=u"Please enter your full Serebii.net forums profile URL, e.g. https://forums.serebii.net/members/dragonfree.388/", force_download=True)

    def clean(self):
        if 'profile_url' in self.cleaned_data:
            profile_page = self.cleaned_data['profile_url']

            # Update/create member info as appropriate
            self.member = profile_page.object
            self.member.save()

            # Check if there is already a user associated with this member
            user = User.objects.filter(member=self.member).order_by('verified', 'id').first()
            if user:
                raise ValidationError(format_html(
                    u"There is already an existing account for this member under the username <strong>{}</strong>. Please either <a href=\"{}\">log in to that account</a>, <a href=\"{}\">reset its password</a> by verifying that you control this account, or <a href=\"{}\">register a new account</a>.",
                    user.username,
                    reverse('login'),
                    reverse('reset_password', kwargs={'pk': user.pk}),
                    reverse('register')
                ))
        return self.cleaned_data

    def create_temp_user(self):
        if not self.is_valid():
            raise ValidationError(u"A temporary user cannot be created.")

        username = re.sub(r'[^\w.@+-]', '', self.member.username)

        while User.objects.filter(username=username).exists():
            username += "-%s" % get_random_string(5)

        password = get_random_string(20)
        user = User.objects.create_user(username=username, password=password, member=self.member)

        user = authenticate(username=username, password=password)
        return user
