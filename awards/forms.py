from collections import defaultdict
from django import forms
from django.db import IntegrityError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.formsets import BaseFormSet
from django.forms.models import ModelChoiceIterator
from django.utils.html import mark_safe
from awards.models import Award, YearAward, Nomination, Vote, Phase, CURRENT_YEAR, check_eligible
from serebii.models import Member, MemberPage, Fic, FicPage
from serebii.forms import SerebiiLinkField


class YearAwardForm(forms.Form):
    include = forms.BooleanField(required=False)

    def __init__(self, year, award, *args, **kwargs):
        self.year = year
        self.award = award
        super(YearAwardForm, self).__init__(*args, **kwargs)

    def save(self):
        if self.cleaned_data['include']:
            obj, _ = YearAward.objects.get_or_create(year=self.year, award=self.award)
            return obj
        else:
            YearAward.objects.filter(year=self.year, award=self.award).delete()
            return None


class BaseYearAwardFormSet(BaseFormSet):
    def __init__(self, year, *args, **kwargs):
        self.year = year
        super(BaseYearAwardFormSet, self).__init__(*args, **kwargs)

        # Base the initial data on either the YearAwards we currently have for this year or what we set for last year.
        existing_data = YearAward.objects.from_year(year) or YearAward.objects.from_year(self.year - 1)
        existing_set = set()
        for obj in existing_data:
            existing_set.add(obj.award.pk)

        self.initial = [
            {
                'year': year,
                'award': award,
                'initial': {
                    'include': award.pk in existing_set or not existing_set,
                }
            } for award in Award.objects.all()
        ]

    def _construct_form(self, i, **kwargs):
        defaults = self.initial[i]
        defaults.update(**kwargs)
        return super(BaseYearAwardFormSet, self)._construct_form(i, **defaults)

    def save(self):
        objects = []
        for form in self.forms:
            obj = form.save()
            if obj is not None:
                objects.append(obj)
        return objects


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ('username', 'user_id')


class FicForm(forms.ModelForm):
    class Meta:
        model = Fic
        fields = ('title', 'authors', 'thread_id', 'post_id')


class IsPostLinkWidget(forms.CheckboxInput):
    template_name = 'widgets/is_post_link.html'


class SerebiiObjectWidget(forms.MultiWidget):
    """
    A widget for entering a link to a fic/profile, used for nominating.
    SerebiiObjectField handles giving this the correct component
    widgets, which are 1) a drop-down with a list of objects of the
    appropriate type that already exist in the system, and 2) a text
    field into which a link can be entered.

    """
    template_name = 'widgets/serebii_object.html'

    def __init__(self, object_class, *args, **kwargs):
        self.object_class = object_class
        super(SerebiiObjectWidget, self).__init__(*args, **kwargs)

    def decompress(self, value):
        if value:
            # Value should be a Fic object or a Member object
            if isinstance(value, self.object_class):
                if value.pk is not None:
                    # An existing fic/member: select that fic/member in the first subwidget
                    decompressed = [value.pk, '']
                else:
                    # A not-yet-existing fic/member: put its link in the second widget
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


class SerebiiObjectSelect(forms.Select):
    """
    A customized Select that restricts the actual choices given to
    those already nominated this year and the given value (if it
    exists).

    """
    def __init__(self, object_class, *args, **kwargs):
        self.object_class = object_class
        super(SerebiiObjectSelect, self).__init__(*args, **kwargs)

    def optgroups(self, name, value, attrs=None):
        groups = super(SerebiiObjectSelect, self).optgroups(name, value, attrs)

        for val in value:
            if val and val not in (choice[0] for choice in self.choices):
                # The defined value is not in the available choices - check if it's a valid fic/member
                selected_object = self.object_class.objects.filter(pk=val).first()
                if selected_object:
                    # We have a submitted value that's the PK for a fic/member - include that fic/member as a choice
                    index = len(groups)
                    groups.append((None, [
                        self.create_option(
                            name,
                            selected_object.pk,
                            str(selected_object),
                            True,
                            index,
                            subindex=None,
                            attrs=attrs
                        )
                    ], index))
        return groups


class SerebiiObjectIterator(ModelChoiceIterator):
    """
    A version of ModelChoiceIterator that limits the displayed choices
    to those objects that have been nominated in the current year.

    """
    def __init__(self, field):
        super(SerebiiObjectIterator, self).__init__(field)
        self.queryset = self.queryset.nominated_in_year(CURRENT_YEAR)


class SerebiiObjectChoiceField(forms.ModelChoiceField):
    def _get_choices(self):
        return SerebiiObjectIterator(self)

    choices = property(_get_choices, forms.ChoiceField._set_choices)


class SerebiiObjectField(forms.MultiValueField):
    """
    A field for entering a fic or member on Serebii.

    """
    empty_values = [None, '', ('', ''), ('', '', False)]

    def __init__(self, page_class, *args, **kwargs):
        # Must pretend the field isn't required even if it is, so that
        # MultiValueField's clean() won't stop us in our tracks later.
        self.really_required = kwargs.pop('required', True)
        self.object_class = page_class.object_class
        # The actual field's queryset argument needs to be the entire collection of fics/members
        object_dropdown = SerebiiObjectChoiceField(queryset=self.object_class.objects.all(), widget=SerebiiObjectSelect(self.object_class))
        fields = [
            object_dropdown,
            SerebiiLinkField(page_class)
        ]
        if self.object_class == Fic:
            fields.append(forms.BooleanField(required=False, widget=IsPostLinkWidget()))
        super(SerebiiObjectField, self).__init__(fields, *args, required=False, **kwargs)

        self.widget = SerebiiObjectWidget(self.object_class, [field.widget for field in self.fields])

    def validate(self, value):
        # Validate requiredness, since we bypass MultiValueField's
        # normal requiredness validation.
        if self.really_required and value is None:
            raise ValidationError(self.error_messages['required'], code='required')

    def compress(self, data_list):
        if data_list:
            if data_list[0]:
                # We have an existing fic/member selected
                return data_list[0]
            elif data_list[1]:
                # Return the object of the FicPage/MemberPage.
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
                raise ValidationError(u"Invalid Fic URL. Please enter the full URL to a thread or post on the Serebii.net forums.")
            thread_id = params.get('thread_id')
            if not thread_id:
                # We don't actually have a thread ID
                raise ValidationError(u"You have entered a link to a post with no thread ID, but not checked the single-post fic box. Please enter a thread link.")
            # Set the link to the thread link instead of the post before we clean
            value[1] = Fic(thread_id=thread_id).link()
        # Just save during clean - having more fics/members in the
        # database can only be a good thing.
        value = super(SerebiiObjectField, self).clean(value)

        # Validate eligibility
        check_eligible(value.get_page())

        if value is not None:
            value.save()
        return value


class NominationForm(forms.ModelForm):
    """
    The form for a single nomination.

    """
    nominee = SerebiiObjectField(MemberPage, help_text=u"Select the user from the drop-down or paste their profile URL into the text field.")
    fic = SerebiiObjectField(FicPage, help_text=u"Select the fic from the drop-down or paste a link to it into the text field.")

    class Meta:
        model = Nomination
        fields = ('nominee', 'fic', 'detail', 'link', 'comment')

    def __init__(self, year, member, award, user, *args, **kwargs):
        self.year = year
        self.member = member
        self.award = award
        self.user = user

        super(NominationForm, self).__init__(*args, **kwargs)

        self.instance.award = self.award

        # Remove fields that don't apply to this award
        if not self.award.has_person:
            del self.fields['nominee']

        if not self.award.has_fic:
            del self.fields['fic']

        if not self.award.has_detail:
            del self.fields['detail']

        if not self.award.has_samples:
            del self.fields['link']

    @property
    def bound_fields(self):
        return iter(self)

    def is_empty(self):
        def tuplify_list(value):
            if isinstance(value, list):
                return tuple(value)
            return value
        return all(tuplify_list(self[field].data) in self.fields[field].empty_values for field in self.fields)

    def is_unset(self):
        return not self.is_bound and self.instance.pk is None or self.is_empty()

    def is_distinct_from(self, form):
        """
        Returns True if this form represents a different nomination
        from the given form and False otherwise.

        """
        distinguishing_fields = [field for field in ('nominee', 'fic', 'detail') if field in self.fields]
        for field in distinguishing_fields:
            self_field = self.cleaned_data[field] if self.has_changed() else getattr(self.instance, field)
            other_field = form.cleaned_data[field] if form.has_changed() else getattr(form.instance, field)
            if self_field != other_field:
                return True
        return False

    def _clean_fields(self):
        # Don't clean fields if the form is empty.
        if self.is_empty():
            return
        super(NominationForm, self)._clean_fields()

    def _post_clean(self):
        # The super method is responsible for running model cleaning.
        # We don't actually want that if the form is empty, so only
        # call super if it isn't.
        if self.is_empty():
            return
        self.instance.year = self.year
        self.instance.member = self.member
        self.instance.award = self.award
        super(NominationForm, self)._post_clean()

    def save(self, commit=True):
        if self.is_empty():
            # The form is empty - clear any existing nomination
            if commit and self.instance.pk is not None:
                self.instance.delete()
            return None
        else:
            instance = super(NominationForm, self).save(commit=False)
            instance.year = self.year
            instance.member = self.member
            instance.award = self.award
            instance.verified = self.user.is_staff or self.user.member == self.member and self.user.verified
            if commit:
                instance.save()
            return instance


class BaseNominationFormSet(BaseFormSet):
    """
    The formset for the full nomination form.

    """
    def __init__(self, year, member, user, *args, **kwargs):
        self.year = year
        self.member = member
        super(BaseNominationFormSet, self).__init__(*args, **kwargs)

        if self.member:
            existing_data = self.member.nominations_by.from_year(year).order_by('pk')
        else:
            existing_data = []

        existing_dict = {}
        for nomination in existing_data:
            if nomination.award_id in existing_dict:
                existing_dict[nomination.award_id].append(nomination)
            else:
                existing_dict[nomination.award_id] = [nomination]

        self.initial = []
        for year_award in YearAward.objects.from_year(year).prefetch_related('award__category'):
            for i in range(2):
                form_kwargs = {
                    'year': year,
                    'member': member,
                    'award': year_award.award,
                    'user': user
                }
                try:
                    form_kwargs['instance'] = existing_dict.get(year_award.award.pk, [])[i]
                except IndexError:
                    pass
                self.initial.append(form_kwargs)

    def _construct_form(self, i, **kwargs):
        defaults = self.initial[i]
        defaults['empty_permitted'] = True  # All forms are allowed to be empty
        defaults.update(**kwargs)
        return super(BaseNominationFormSet, self)._construct_form(i, **defaults)

    def clean(self):
        phase = Phase.get_current()
        if phase > 'nomination':
            raise ValidationError(u"The nomination phase has ended! Better luck next year.")
        elif phase < 'nomination':
            raise ValidationError(u"The nomination phase hasn't started yet! Have patience until nominations open.")
        # By this point all nominations will have been saved to the
        # database, so we can safely assume they have PKs.
        fic_nominations = defaultdict(int)
        person_nominations = defaultdict(int)
        award_dict = defaultdict(list)

        for form in self.forms:
            if not form.is_empty() and form.is_valid():
                if 'fic' in form.fields:
                    if form.has_changed():
                        fic = form.cleaned_data['fic']
                    else:
                        fic = form.instance.fic
                    fic_nominations[fic] += 1
                    for author in fic.authors.all():
                        person_nominations[author] += 1
                if 'nominee' in form.fields:
                    if form.has_changed():
                        author = form.cleaned_data['nominee']
                    else:
                        author = form.instance.nominee
                    person_nominations[author] += 1
                if form.award in award_dict:
                    for other_form in award_dict[form.award]:
                        if not form.is_distinct_from(other_form):
                            form.errors['__all__'] = form.error_class([u"You cannot make the same nomination twice in the same category."])
                award_dict[form.award].append(form)

        for (fic, nominations) in fic_nominations.items():
            if nominations > settings.MAX_FIC_NOMINATIONS:
                raise ValidationError(u"You have nominated %(fic)s %(nominations)s times. You may only nominate any given fic up to %(max_nominations)s times. Please remove some nominations for %(fic)s." % {'fic': fic, 'nominations': nominations, 'max_nominations': settings.MAX_FIC_NOMINATIONS})

        for (person, nominations) in person_nominations.items():
            if nominations > settings.MAX_PERSON_NOMINATIONS:
                raise ValidationError(u"You have nominated %(person)s or their work %(nominations)s times. You may only nominate a given person up to %(max_nominations)s times. Please remove some nominations for %(person)s." % {'person': person, 'nominations': nominations, 'max_nominations': settings.MAX_PERSON_NOMINATIONS})

        if len(person_nominations) < settings.MIN_DIFFERENT_NOMINATIONS:
            raise ValidationError(u"You must nominate at least %s different authors." % settings.MIN_DIFFERENT_NOMINATIONS)

    def save(self):
        return [form.save() for form in self.forms if form.has_changed()]


class VotingForm(forms.Form):
    """
    The full voting form.

    """
    def __init__(self, year, member, *args, **kwargs):
        self.year = year
        self.member = member

        super(VotingForm, self).__init__(*args, **kwargs)

        current_votes = {}

        for vote in Vote.objects.from_year(self.year).filter(member=self.member):
            current_votes[vote.award_id] = vote.nomination

        for year_award in YearAward.objects.from_year(year).select_related('award'):
            nominations = year_award.get_nominations()
            if nominations:
                field = forms.ModelChoiceField(queryset=nominations, label=year_award.award.name, widget=forms.RadioSelect, empty_label="No vote", required=False, initial=current_votes.get(year_award.award_id))
                field.award = year_award.award
                self.fields['award_%s' % year_award.award.pk] = field

    def clean(self):
        phase = Phase.get_current()
        if phase > 'voting':
            raise ValidationError(u"The voting phase has ended! Better luck next year.")
        elif phase < 'voting':
            raise ValidationError(u"The voting phase hasn't started yet! Have patience until voting opens.")

        votes = []
        for field in self.fields:
            vote = self.cleaned_data.get(field)
            if vote:
                vote_obj = Vote(member=self.member, year=self.year, award_id=self.fields[field].award.pk, nomination=vote)
                try:
                    vote_obj.clean()
                except ValidationError as e:
                    self.add_error(field, e)
                votes.append(vote_obj)
        if len(votes) * 2 < len(self.fields):
            raise ValidationError(u"You must place a vote in at least half of the available categories.")
        return self.cleaned_data

    def save(self, commit=True):
        votes = []
        for year_award in YearAward.objects.from_year(self.year):
            vote = self.cleaned_data.get('award_%s' % year_award.award_id)
            if vote:
                try:
                    vote_obj = Vote.objects.from_year(self.year).get(member=self.member, award_id=year_award.award_id)
                except Vote.DoesNotExist:
                    vote_obj = Vote(member=self.member, year=self.year, award_id=year_award.award_id)
                vote_obj.nomination = vote
                if commit:
                    vote_obj.save()
                votes.append(vote_obj)
        return votes
