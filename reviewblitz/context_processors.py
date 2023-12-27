from django.conf import settings
from reviewblitz.models import ReviewBlitz

def current_blitz(request):
    return {'current_blitz': ReviewBlitz.get_current()}
