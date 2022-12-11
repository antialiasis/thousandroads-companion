from django.db.models import Sum, F, Count
from django.db.models.functions import Least, Floor
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, FormView
from django.contrib import messages

from forum.views import LoginRequiredMixin, VerificationRequiredMixin
from reviewblitz.models import BlitzReview, ReviewBlitz
from reviewblitz.forms import BlitzReviewSubmissionForm


class BlitzReviewSubmissionFormView(LoginRequiredMixin, VerificationRequiredMixin, FormView):
    form_class = BlitzReviewSubmissionForm
    template_name = "blitz_review_submit.html"

    def form_valid(self, form):
        review = form.cleaned_data["review"]
        review.chapters = form.cleaned_data["chapters"]
        review.save()

        blitz = ReviewBlitz.get_current()
        week_index = BlitzReview(blitz=blitz, review=review).week_index()
        print(f"This review was posted in week {week_index} of the Blitz.")

        prev_reviews = BlitzReview.objects.filter(blitz=blitz, review__author=review.author, review__fic=review.fic)

        prev_chapters_reviewed = 0
        has_claimed_weekly_theme = False
        for r in prev_reviews:
            effective_chapters_reviewed = min(r.review.word_count // blitz.scoring.words_per_chapter, r.review.chapters)
            prev_chapters_reviewed += effective_chapters_reviewed
            if r.week_index() == week_index and r.theme:
                has_claimed_weekly_theme = True
            print(f"Previous review - effective chapters reviewed: {effective_chapters_reviewed}, week index: {r.week_index()}, weekly theme claimed: {has_claimed_weekly_theme}")

        effective_chapters_reviewed = min(review.word_count // blitz.scoring.words_per_chapter, review.chapters)
        print(f"Effective chapters reviewed for this review: {effective_chapters_reviewed}")

        score = effective_chapters_reviewed * blitz.scoring.chapter_points
        print(f"Base score: {score}")

        # Check how many consecutive chapter intervals we tick over with this review.
        chapter_bonuses = (effective_chapters_reviewed + prev_chapters_reviewed) // blitz.scoring.consecutive_chapter_interval - prev_chapters_reviewed // blitz.scoring.consecutive_chapter_interval
        print(f"Chapter bonuses: {chapter_bonuses}")
        score += chapter_bonuses * blitz.scoring.consecutive_chapter_bonus

        if form.cleaned_data["satisfies_theme"] and not has_claimed_weekly_theme:
            print(f"Claiming weekly theme - +{blitz.scoring.theme_bonus} points!")
            score += blitz.scoring.theme_bonus

        BlitzReview.objects.create(
            blitz=blitz,
            review=review,
            theme=form.cleaned_data["satisfies_theme"],
            score=score,
        )
        messages.success(self.request, "Your review has been submitted and is pending approval.")
        return HttpResponseRedirect(reverse("home"))

    def get_form_kwargs(self):
        kwargs = super(BlitzReviewSubmissionFormView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class BlitzReviewApprovalQueueView(PermissionRequiredMixin, ListView):
    template_name = "blitz_review_approval_queue.html"
    permission_required = "reviewblitz.approve"

    def get_queryset(self):
        return BlitzReview.objects.filter(approved=False)

    def post(self, request, *args, **kwargs):
        blitz_review_obj = BlitzReview.objects.get(id=request.POST.get("blitz_review_id"))
        if request.POST.get("valid"):
            blitz_review_obj.approved = True
            blitz_review_obj.save(update_fields=("approved",))
            messages.success(request, f"{blitz_review_obj.review} was approved.")
        else:
            blitz_review_obj.delete()
            messages.warning(
                request,
                f"{blitz_review_obj.review} was rejected. Please remember to inform {blitz_review_obj.review.author}."
            )
        return HttpResponseRedirect(reverse("blitz_review_approval_queue"))


class BlitzLeaderboardView(ListView):
    template_name = "blitz_leaderboard.html"
    context_object_name = "leaderboard"

    def get_queryset(self):
        return BlitzReview.objects.filter(blitz=ReviewBlitz.get_current(), approved=True).values('review__author').annotate(points=Sum('score'), reviews=Count('review'), chapters=Sum('review__chapters'), words=Sum('review__word_count'), username=F('review__author__username')).order_by('-points')
