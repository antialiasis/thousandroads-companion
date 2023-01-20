from django import forms
from django.forms.formsets import formset_factory
from django.core.exceptions import ValidationError
from forum.forms import ForumLinkField, ForumObjectField
from forum.models import ReviewPage, ChapterPage
from reviewblitz.models import BlitzReview, ReviewBlitz


class ReviewField(forms.Field):
    def to_python(self, value):
        try:
            review = ReviewPage.from_url(value).object
        except ValueError as e:
            raise ValidationError("Invalid review URL", code="invalid") from e

        if BlitzReview.objects.filter(blitz=ReviewBlitz.get_current(), review=review).exists():
            raise ValidationError("This review has already been submitted.", code="invalid")

        return review


class ChapterLinkForm(forms.Form):
    chapter = ForumObjectField(ChapterPage, label="Chapter link")


ChapterLinkFormSet = formset_factory(ChapterLinkForm, extra=1)


class BlitzReviewSubmissionForm(forms.Form):
    review = ReviewField(label="Review link", help_text="You can find this link by clicking the date near the top left corner of your review post on the Thousand Roads forums.")
    # Entering very large numbers of chapters causes an error to be thrown
    # as the integer becomes too large to be stored in the db field
    # This may have been fixed in later Django releases
    # https://code.djangoproject.com/ticket/12030
    chapters = forms.IntegerField(min_value=1, max_value=1000, initial=1, help_text="The number of chapters covered by this review.")
    satisfies_theme = forms.BooleanField(label="Satisfies theme", required=False, help_text="Check this box if your review satisfied the active weekly Review Blitz theme at the time of its posting (see Review Blitz thread on the forums).")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(BlitzReviewSubmissionForm, self).__init__(*args, **kwargs)

        formset_prefix = "chapter_links"
        if kwargs.get("prefix"):
            formset_prefix = kwargs["prefix"] + "-" + formset_prefix
        self.chapter_link_formset = ChapterLinkFormSet(prefix=formset_prefix, data=kwargs.get('data'))

    def clean_review(self):
        review = self.cleaned_data["review"]
        print(f"Review author: {review.author=}")
        print(f"User: {self.user.member=}")
        if review.author != self.user.member:
            author = review.author
            review.delete()
            raise ValidationError(
                "This review was written by %(author)s, not you!",
                code="forbidden",
                params={"author": author}
            )
        blitz = ReviewBlitz.get_current()
        if review.word_count < blitz.scoring.min_words:
            raise ValidationError("This review does not meet the minimum word count for this Review Blitz! Please submit a review at least {} words long.".format(blitz.scoring.min_words))
        if review.posted_date < blitz.start_date:
            raise ValidationError("This review was posted before the start of this Blitz!")
        if review.posted_date >= blitz.end_date:
            raise ValidationError("This review was posted after the end of this Blitz!")
        return review

    def clean(self):
        cleaned_data = super().clean()

        self.chapter_link_formset.full_clean()

        cleaned_data["chapter_links"] = []

        if "review" in cleaned_data:
            for form in self.chapter_link_formset:
                if "chapter" in form.cleaned_data:
                    chapter = form.cleaned_data["chapter"]
                    if chapter:
                        if chapter.fic != cleaned_data["review"].fic:
                            form.add_error('chapter', "This is not a chapter of the fic the review is on!")
                        else:
                            cleaned_data["chapter_links"].append(chapter)

        return cleaned_data

    def is_valid(self):
        is_valid = super().is_valid()
        formset_is_valid = self.chapter_link_formset.is_valid()
        return is_valid and formset_is_valid
