from django import forms
from django.core.exceptions import ValidationError
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


class BlitzReviewSubmissionForm(forms.Form):
    review = ReviewField(label="Review link", help_text="You can find this link by clicking the date near the top left corner of your review post on the Thousand Roads forums.")
    # Entering very large numbers of chapters causes an error to be thrown
    # as the integer becomes too large to be stored in the db field
    # This may have been fixed in later Django releases
    # https://code.djangoproject.com/ticket/12030
    chapters = forms.IntegerField(min_value=1, max_value=1000, initial=1, help_text="The number of chapters covered by this review.")
    satisfies_theme = forms.BooleanField(label="Satisfies theme", required=False, help_text="Check this box if your review satisfied the active weekly Review Blitz theme at the time of its posting (see Review Blitz thread on the forums).")
    chapter_links = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(BlitzReviewSubmissionForm, self).__init__(*args, **kwargs)

        blitz = ReviewBlitz.get_current()
        self.fields["chapter_links"].help_text = "If some of the chapters you read were {} words or more, enter their links here, one in each line, to receive a bonus of {} points per chapter.".format(blitz.scoring.long_chapter_bonus_words, blitz.scoring.long_chapter_bonus)

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

    def clean_chapter_links(self):
        links = self.cleaned_data["chapter_links"].strip()
        if not links:
            return []

        chapter_links = links.split('\n')

        chapters = []

        for link in chapter_links:
            link = link.strip()
            if not link:
                continue

            try:
                chapter = ChapterPage.from_url(link).object
            except ValueError as e:
                raise ValidationError("Invalid chapter URL!", code="invalid") from e

            chapters.append(chapter)

        return list(set(chapters))

    def clean(self):
        cleaned_data = super().clean()

        if "chapter_links" in cleaned_data and "review" in cleaned_data:
            for chapter in cleaned_data["chapter_links"]:
                if chapter.fic != cleaned_data["review"].fic:
                    raise ValidationError("This is not a chapter of the fic the review is on!", code="invalid")

        return cleaned_data
