from django import forms
from django.core.exceptions import ValidationError
from forum.models import ReviewPage
from reviewblitz.models import BlitzReview, ReviewBlitz


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
    # Entering very large numbers of chapters causes an error to be thrown
    # as the integer becomes too large to be stored in the db field
    # This may have been fixed in later Django releases
    # https://code.djangoproject.com/ticket/12030
    chapters = forms.IntegerField(min_value=1, max_value=1000)
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
        blitz = ReviewBlitz.get_current()
        if review.word_count < blitz.scoring.min_words:
            raise ValidationError("This review does not meet the minimum word count for this Review Blitz! Please submit a review at least {} words long.".format(blitz.scoring.min_words))
        if review.posted_date < blitz.start_date:
            raise ValidationError("This review was posted before the start of this Blitz!")
        if review.posted_date >= blitz.end_date:
            raise ValidationError("This review was posted after the end of this Blitz!")
        return review
