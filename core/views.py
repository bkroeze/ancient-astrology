from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone

from natal.clients import ChartRequest, ChartAPIError, generate_chart


def home(request):
    """Home page view."""
    context = {}
    user = request.user
    
    if user.is_authenticated:
        # Check if wizard should be shown
        if user.default_place is None and user.onboarding_dismissed_at is None:
            # User needs to complete onboarding
            context['show_wizard'] = True
        elif user.default_place:
            # User has default place - show chart-of-now
            try:
                place = user.default_place
                chart_request = ChartRequest(
                    latitude=float(place.latitude),
                    longitude=float(place.longitude),
                    datetime=timezone.now(),
                    format='svg'
                )
                chart = generate_chart(chart_request)
                context['chart'] = chart
            except ChartAPIError as e:
                context['chart_error'] = str(e)
    
    return render(request, 'core/home.html', context)


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


def chart_of_now(request):
    """
    HTMX endpoint for rendering the chart-of-now widget.

    This view generates a chart for the current moment at the user's
    default location. It is called by the home page on load and by
    JavaScript on idle-timeout to refresh the chart.
    """
    context = {}

    # User must be authenticated and have a default place set
    if not request.user.is_authenticated or request.user.default_place is None:
        return render(request, 'core/chart_of_now.html', context, content_type='text/html')

    place = request.user.default_place
    chart_request = ChartRequest(
        latitude=float(place.latitude),
        longitude=float(place.longitude),
        datetime=timezone.now(),
        format='svg',
    )

    try:
        chart = generate_chart(chart_request)
        context['chart'] = chart
    except ChartAPIError as e:
        context['error'] = str(e)

    return render(request, 'core/chart_of_now.html', context, content_type='text/html')
