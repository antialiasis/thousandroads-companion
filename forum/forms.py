import re
import requests
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.html import format_html, mark_safe
from django.utils.text import slugify
from forum.models import Member, User, MemberPage, Fic


class ForumLinkField(forms.CharField):
    """
    A field for a link to a ForumPage.

    """
    empty_values = [None]

    def __init__(self, page_class, *args, **kwargs):
        self.page_class = page_class
        self.force_download = kwargs.pop('force_download', False)
        super(ForumLinkField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(ForumLinkField, self).to_python(value)
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


class IsPostLinkWidget(forms.CheckboxInput):
    template_name = 'widgets/is_post_link.html'


class ForumObjectWidget(forms.MultiWidget):
    """
    A widget for entering a link to a forum object.
    ForumObjectField handles giving this the correct component
    widgets, which are 1) something to select an object that exists in
    the system, and 2) a text field into which a link can be entered.

    """
    template_name = 'widgets/forum_object.html'

    def __init__(self, object_class, *args, **kwargs):
        self.object_class = object_class
        super(ForumObjectWidget, self).__init__(*args, **kwargs)

    def decompress(self, value):
        if value:
            # Value should be a forum object of the correct type
            if isinstance(value, self.object_class):
                if value.pk is not None:
                    # An existing object: select that fic/member in the first subwidget
                    decompressed = [value.pk, '']
                else:
                    # A not-yet-existing object: put its link in the second widget
                    decompressed = [None, value.link()]
            else:
                # value is probably a primary key
                decompressed = [value, '']
        else:
            decompressed = [None, '']

        if self.object_class == Fic:
            # Add an appropriate value for the post link field.
            decompressed.append(bool(isinstance(value, Fic) and value.post_id))
        return decompressed


class ForumObjectField(forms.MultiValueField):
    """
    A field for entering an object on the forum.

    """
    empty_values = [None, '', ('', ''), ('', '', False)]

    def __init__(self, page_class, *args, **kwargs):
        # Must pretend the field isn't required even if it is, so that
        # MultiValueField's clean() won't stop us in our tracks later.
        self.really_required = kwargs.pop('required', True)
        self.object_class = page_class.object_class
        fields = [
            self.get_object_field(),
            ForumLinkField(page_class)
        ]
        if self.object_class == Fic:
            fields.append(forms.BooleanField(required=False, widget=IsPostLinkWidget()))
        super(ForumObjectField, self).__init__(fields, *args, required=False, **kwargs)

        self.widget = ForumObjectWidget(self.object_class, [field.widget for field in self.fields])

    def get_object_field(self):
        return forms.ModelChoiceField(queryset=self.object_class.objects.all(), widget=forms.HiddenInput)

    def validate(self, value):
        # Validate requiredness, since we bypass MultiValueField's
        # normal requiredness validation.
        if self.really_required and value is None:
            raise ValidationError(self.error_messages['required'], code='required')

    def compress(self, data_list):
        if data_list:
            if data_list[0]:
                # We have an existing object selected
                return data_list[0]
            elif data_list[1]:
                # Return the object of the page.
                return data_list[1].object
        return None

    def prepare_value(self, value):
        if isinstance(value, self.object_class):
            return value.pk
        return value

    def clean(self, value):
        if self.object_class == Fic and value[1] and not value[2]:
            # We have a link, and we haven't checked the post link box - make
            # sure the link is a thread link
            try:
                params = FicPage.get_params_from_url(value[1])
            except ValueError:
                raise ValidationError(u"Invalid Fic URL. Please enter the full URL to a thread or post on the %s forums." % settings.FORUM_NAME)
            thread_id = params.get('thread_id')
            if not thread_id:
                # We don't actually have a thread ID
                raise ValidationError(u"You have entered a link to a post with no thread ID, but not checked the single-post fic box. Please enter a thread link.")
            # Set the link to the thread link instead of the post before we clean
            value[1] = Fic(thread_id=thread_id).link()

        # Just save during clean - nothing wrong with more forum objects
        # in the database.
        value = super(ForumObjectField, self).clean(value)

        print("Cleaning forum object field value - %s" % value)

        if value is not None:
            value.save()
        return value


class CatalogSearchForm(forms.Form):
    query = forms.CharField(widget=forms.TextInput(attrs={'type': 'search', 'class': 'form-control'}))

    def get_results(self):
        if self.is_valid():
            query = self.cleaned_data['query']
            return Fic.objects.filter(Q(tags__tag__icontains=query) | Q(title__icontains=query) | Q(summary__icontains=query))
        return []


class CatalogFicForm(forms.ModelForm):
    tags = forms.CharField(required=False)

    class Meta:
        model = Fic
        fields = ('summary', 'genres', 'completed')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tags'].initial = ', '.join([tag.tag for tag in self.instance.tags.all()])

    def clean_tags(self):
        return [slugify(tag) for tag in self.cleaned_data['tags'].split(',') if slugify(tag)]

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
            raise ValidationError(u"This user has not connected a %s account and therefore cannot be verified. You should probably register a new account." % settings.FORUM_NAME)
        self.user = user
        return self.cleaned_data


class PasswordResetForm(forms.Form):
    """
    A password reset form that verifies a verification code on the
    user's forum profile page rather than sending e-mails.

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
    profile_url = ForumLinkField(MemberPage, label=u"Profile URL", help_text=u"Please enter your full forum profile URL, e.g. https://%smembers/dragonfree.388/" % settings.FORUM_URL, force_download=True)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(VerificationForm, self).__init__(*args, **kwargs)
        if user.member:
            del self.fields['profile_url']

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
    profile_url = ForumLinkField(MemberPage, label=u"Profile URL", help_text=u"Please enter your full forum profile URL, e.g. https://%smembers/dragonfree.388/" % settings.FORUM_URL, force_download=True)

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
