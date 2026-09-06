from django.http import HttpResponse


def health(request):
    """Liveness probe. Task 2 moves this behind the split settings."""
    return HttpResponse("ok", content_type="text/plain")
