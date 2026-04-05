from django.shortcuts import render
from django.http import HttpResponse


def home(request):
    """Home page view."""
    return render(request, 'core/home.html')


def htmx_partial(request):
    """
    HTMX partial view for demonstrating HTMX partial rendering.
    Returns a partial HTML snippet suitable for HTMX swapping.
    
    This view demonstrates:
    - HTMX request detection via request.htmx
    - CSRF-protected POST handling
    - Partial content rendering
    """
    if request.htmx:
        # Return partial HTML for HTMX requests
        return HttpResponse(
            '<div class="htmx-result"><p>HTMX request detected! Timestamp: '
            f'<span id="timestamp">{request.htmx.current_url}</span></p></div>',
            content_type='text/html'
        )
    
    # For non-HTMX requests, return a minimal HTML page
    return HttpResponse(
        '<html><body><div class="htmx-result">Non-HTMX fallback</div></body></html>',
        content_type='text/html'
    )
