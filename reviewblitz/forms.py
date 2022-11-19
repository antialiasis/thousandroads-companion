from django import forms
from django.core.exceptions import ValidationError
from forum.models import ReviewPage
from reviewblitz.models import BlitzReview


class ReviewField(forms.Field):
    def to_python(self, value):
        try:
            review = ReviewPage.from_url(value).object
        except ValueError as e:
            raise ValidationError("Invalid review URL", code="invalid") from e

        if BlitzReview.objects.filter(review=review).exists():
            raise ValidationError("This review has already been submitted.", code="invalid")

        return review


class BlitzReviewSubmissionForm(forms.Form):
    review = ReviewField(label="Review link")
    chapters = forms.IntegerField(min_value=1)
    satisfies_theme = forms.BooleanField(label="Satisfies theme", required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(BlitzReviewSubmissionForm, self).__init__(*args, **kwargs)

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
        return review
