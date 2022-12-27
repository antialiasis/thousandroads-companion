from django.db.models import Sum, F, Count, Max
from django.db.models.functions import Least, Floor, Coalesce
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, FormView, TemplateView
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist

from forum.views import LoginRequiredMixin, VerificationRequiredMixin
from reviewblitz.models import BlitzReview, ReviewBlitz, ReviewChapterLink, BlitzUser
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

        long_chapters = []
        for chapter in form.cleaned_data["chapter_links"]:
            if chapter.word_count >= blitz.scoring.long_chapter_bonus_words:
                score += blitz.scoring.long_chapter_bonus
                long_chapters.append(chapter)

        blitzreview = BlitzReview.objects.create(
            blitz=blitz,
            review=review,
            theme=form.cleaned_data["satisfies_theme"],
            score=score,
        )

        for chapter in long_chapters:
            chapter.save()
            ReviewChapterLink.objects.create(
                review=blitzreview,
                chapter=chapter
            )

        # If the user hasn't already gotten their own "blitz user" instance,
        # create one now
        BlitzUser.objects.get_or_create(blitz=blitz, member=review.author)

        messages.success(self.request, "Your review has been submitted and is pending approval.")
        return HttpResponseRedirect(reverse("blitz_user"))

    def get_form_kwargs(self):
        kwargs = super(BlitzReviewSubmissionFormView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class BlitzReviewApprovalQueueView(PermissionRequiredMixin, ListView):
    template_name = "blitz_review_approval_queue.html"
    permission_required = "reviewblitz.approve"

    def get_queryset(self):
        return BlitzReview.objects.filter(approved=False, blitz=ReviewBlitz.get_current())

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
        return BlitzReview.objects.filter(blitz=ReviewBlitz.get_current(), approved=True).values('review__author').annotate(points=Sum('score') + Coalesce(Max('review__author__blitz_members__bonus_points'), 0), reviews=Count('review'), chapters=Sum('review__chapters'), words=Sum('review__word_count'), username=F('review__author__username')).order_by('-points')

class BlitzUserView(LoginRequiredMixin, TemplateView):
    template_name = "blitz_user.html"

    def get_context_data(self, *args, **kwargs):
        context = super(BlitzUserView, self).get_context_data(*args, **kwargs) 

        # Get user info
        # Any bonuses from prize fulfillment (or other sources)
        # Any points spent for prizes

        user, _ = BlitzUser.objects.get_or_create(blitz=ReviewBlitz.get_current(), member=self.request.user.member)

        try:
            queryset = BlitzReview.objects.filter(blitz=ReviewBlitz.get_current(), review__author=self.request.user.member.user_id).values('review__post_id', 'review__author', 'review__fic__title', 'review__posted_date', 'review__chapters', 'review__word_count', 'theme', 'score').order_by('-review__posted_date')
        except AttributeError:
            # User not verified
            # Query fails because they don't have a user_id
            queryset = BlitzReview.objects.none()

        approved_reviews = queryset.filter(blitz=ReviewBlitz.get_current(), approved=True)
        context['approved_reviews'] = approved_reviews

        approved_score = approved_reviews.aggregate(approved_score=Sum('score')).get('approved_score')
        if approved_score is not None:
            context['approved_score'] = approved_score
        else:
            context['approved_score'] = 0

        # Apply any potential bonus points to get effective score
        print(context['approved_score'])
        print(user.bonus_points)
        context['approved_score'] = context['approved_score'] + user.bonus_points

        # Show prize points available by deducting points spent from total score
        context['prize_points'] = context['approved_score'] - user.points_spent

        pending_reviews = queryset.filter(blitz=ReviewBlitz.get_current(), approved=False)
        context['pending_reviews'] = pending_reviews
        context['pending_score'] = pending_reviews.aggregate(approved_score=Sum('score')).get('approved_score')
        return context
