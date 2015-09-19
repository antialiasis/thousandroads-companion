import re
import requests
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.utils.crypto import get_random_string
from bs4 import BeautifulSoup
from serebii.models import Member, User, MemberPage


class SerebiiLinkField(forms.CharField):
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
            raise ValidationError(u"Invalid %s URL. Please ensure that you have entered the full URL including the http:// portion." % self.page_class.__name__, code='invalid')
        return value

    def prepare_value(self, value):
        if not isinstance(value, self.page_class):
            return ''
        return value.get_url()


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username',)


class UserLookupForm(forms.Form):
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


def validate_verification_code(code, soup):
    try:
        bio = soup.find('dt', text=u"Biography:").find_next_sibling('dd')
    except AttributeError:
        raise ValidationError(u"Could not find Biography field on profile page. If you submitted a valid profile link, please contact Dragonfree on the forums with your username so that you can be manually verified.")
    if code not in unicode(bio.get_text()):
        raise ValidationError(u"Your verification code was not found in your profile's Biography section. Please ensure you followed the instructions correctly. If the problem persists, please contact Dragonfree on the forums with your username to be manually verified.")


class PasswordResetForm(forms.Form):
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

        member_page = MemberPage.from_url(self.user.member.link() + '&simple=1', True)
        validate_verification_code(self.user.verification_code, member_page.get_soup())
        return self.cleaned_data

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['password1'])
        if commit:
            self.user.save()
        return self.user



class VerificationForm(forms.Form):
    profile_url = SerebiiLinkField(MemberPage, label=u"Profile URL", help_text=u"Please enter your full Serebii.net forums profile URL, e.g. http://www.serebiiforums.com/member.php?388-Dragonfree", force_download=True)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(VerificationForm, self).__init__(*args, **kwargs)

    def clean(self):
        if 'profile_url' in self.cleaned_data:
            profile_page = self.cleaned_data['profile_url']
            soup = profile_page.get_soup()
            validate_verification_code(self.user.verification_code, soup)
            self.member = profile_page.object
            self.member.save()
        return self.cleaned_data


class TempUserProfileForm(forms.Form):
    profile_url = SerebiiLinkField(MemberPage, label=u"Profile URL", help_text=u"Please enter your full Serebii.net forums profile URL, e.g. http://www.serebiiforums.com/member.php?388-Dragonfree", force_download=True)

    def clean(self):
        if 'profile_url' in self.cleaned_data:
            profile_page = self.cleaned_data['profile_url']

            # Update/create member info as appropriate
            self.member = profile_page.object
            self.member.save()

            # Check if there is already a verified user associated with this memebr
            if User.objects.filter(member=self.member).exists():
                raise ValidationError(u"This member has already registered and verified or submitted votes under another username. Please log in to that account to submit or edit verified votes. If you did not register an account or submit votes, please contact Dragonfree.")
        return self.cleaned_data

    def create_temp_user(self):
        if not self.is_valid():
            raise ValidationError(u"A temporary user cannot be created.")

        username = "%s-%s" % (re.sub(r'[^\w.@+-]', '', self.member.username), get_random_string(5))
        password = get_random_string(20)
        user = User.objects.create_user(username=username, password=password, member=self.member)

        user = authenticate(username=username, password=password)
        return user
