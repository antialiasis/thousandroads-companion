from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, FormView
from django.contrib import messages

from forum.views import VerificationRequiredMixin
from reviewblitz.models import BlitzReview, ReviewBlitz
from reviewblitz.forms import BlitzReviewSubmissionForm


class BlitzReviewSubmissionFormView(VerificationRequiredMixin, FormView):
    form_class = BlitzReviewSubmissionForm
    template_name = "blitz_review_submit.html"

    def form_valid(self, form):
        review = form.cleaned_data["review"]
        review.chapters = form.cleaned_data["chapters"]
        review.save()
        BlitzReview.objects.create(
            blitz=ReviewBlitz.get_current(),
            review=review,
            theme=form.cleaned_data["satisfies_theme"],
            score=0, # TODO: actually calculate score
        )
        messages.success(self.request, "Your review has been submitted and is pending approval.")
        return HttpResponseRedirect(reverse("home"))

    def get_form_kwargs(self):
        kwargs = super(BlitzReviewSubmissionFormView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class BlitzReviewApprovalQueueView(PermissionRequiredMixin, ListView):
    template_name = "blitz_review_approval_queue.html"
    permission_required = "reviewblitz.blitzreview.approve"

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