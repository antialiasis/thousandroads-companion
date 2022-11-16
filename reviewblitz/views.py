from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView
from django.contrib import messages
from reviewblitz.models import BlitzReview


# Create your views here.

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
