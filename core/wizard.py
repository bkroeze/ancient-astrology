"""
Onboarding Wizard views for the guided setup flow.

This module provides HTMX-powered wizard views for new users:
- Step 1: Location input (geolocation or search)
- Step 2: Birth datetime input
- Skip/Dismiss: Mark wizard as complete without setting up
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from natal.clients import reverse_geocode_location, GeocodingError
from natal.models import NatalSet, Place
from users.models import User


@login_required
def wizard_step1(request):
    """
    GET handler for wizard step 1: location input.
    
    Returns the step 1 HTML partial for HTMX to swap in.
    """
    return render(request, 'core/wizard_step1.html', {})


@login_required
def wizard_step2(request):
    """
    GET handler for wizard step 2: birth datetime input.
    
    Returns the step 2 HTML partial for HTMX to swap in.
    Displays the timezone from the user's default_place for confirmation.
    """
    place = request.user.default_place
    context = {}
    if place:
        context['place'] = place
        context['timezone'] = place.timezone
    return render(request, 'core/wizard_step2.html', context)


@require_POST
@login_required
def wizard_step1_submit(request):
    """
    POST handler for wizard step 1 form submission.
    
    Accepts location data from either:
    - Browser geolocation (lat, lon hidden fields)
    - Location search (location_name, lat, lon, timezone from autocomplete)
    
    Creates or reuses a Place, sets as user's default_place, and
    returns step 2 HTML partial via HTMX swap.
    
    On error, returns step 1 with inline error message.
    """
    # Get location data from form
    location_name = request.POST.get('location_name', '').strip()
    lat_str = request.POST.get('latitude', '').strip()
    lon_str = request.POST.get('longitude', '').strip()
    timezone_str = request.POST.get('timezone', '').strip()
    
    # Validate required fields
    if not lat_str or not lon_str:
        return render(request, 'core/wizard_step1.html', {
            'error': 'Please select a location using geolocation or search.'
        })
    
    try:
        lat = Decimal(lat_str)
        lon = Decimal(lon_str)
    except InvalidOperation:
        return render(request, 'core/wizard_step1.html', {
            'error': 'Invalid coordinates. Please try again.'
        })
    
    # If location_name not provided, try reverse geocoding
    if not location_name:
        try:
            geo_result = reverse_geocode_location(float(lat), float(lon))
            if geo_result:
                location_name = geo_result.name
                if not timezone_str:
                    timezone_str = geo_result.timezone or ''
            else:
                return render(request, 'core/wizard_step1.html', {
                    'error': 'Could not identify this location. Please use the search box instead.'
                })
        except GeocodingError:
            return render(request, 'core/wizard_step1.html', {
                'error': 'Location lookup failed. Please use the search box instead.'
            })
    
    # If still no timezone, we can't proceed
    if not timezone_str:
        return render(request, 'core/wizard_step1.html', {
            'error': 'Could not determine timezone for this location. Please use the search box instead.'
        })
    
    # Create or reuse Place
    user = request.user
    try:
        # Try to find existing place with same name for this user
        place = Place.objects.filter(
            name=location_name,
            created_by=user
        ).first()
        
        if not place:
            place = Place.objects.create(
                name=location_name,
                latitude=lat,
                longitude=lon,
                timezone=timezone_str,
                created_by=user
            )
    except Exception:
        return render(request, 'core/wizard_step1.html', {
            'error': 'Failed to save location. Please try again.'
        })
    
    # Set as default_place
    user.default_place = place
    user.save(update_fields=['default_place'])
    
    # Return step 2 partial
    return render(request, 'core/wizard_step2.html', {
        'place': place,
        'timezone': place.timezone
    })


@require_POST
@login_required
def wizard_step2_submit(request):
    """
    POST handler for wizard step 2 form submission.
    
    Accepts birth datetime and optional name, creates a NatalSet
    with location data copied from the user's default_place, and
    returns the chart-of-now partial HTML to swap into the wizard container.
    
    On error, returns step 2 with inline error message.
    """
    birth_datetime_str = request.POST.get('birth_datetime', '').strip()
    name = request.POST.get('name', '').strip()
    
    # Validate birth datetime
    if not birth_datetime_str:
        return render(request, 'core/wizard_step2.html', {
            'place': request.user.default_place,
            'timezone': request.user.default_place.timezone if request.user.default_place else '',
            'error': 'Please enter your birth date and time.'
        })
    
    try:
        # Parse datetime-local input format (YYYY-MM-DDTHH:MM)
        birth_datetime = datetime.fromisoformat(birth_datetime_str)
        
        # Make it timezone-aware using the Place's timezone
        place = request.user.default_place
        if not place:
            return render(request, 'core/wizard_step2.html', {
                'error': 'No default location set. Please go back and set your location.'
            })
        
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(place.timezone)
        birth_datetime = birth_datetime.replace(tzinfo=tz)
    except ValueError:
        return render(request, 'core/wizard_step2.html', {
            'place': request.user.default_place,
            'timezone': request.user.default_place.timezone if request.user.default_place else '',
            'error': 'Invalid date/time format. Please use the date picker.'
        })
    except Exception:
        return render(request, 'core/wizard_step2.html', {
            'place': request.user.default_place,
            'timezone': request.user.default_place.timezone if request.user.default_place else '',
            'error': 'Could not process timezone. Please try again.'
        })
    
    # Use default name if not provided
    if not name:
        name = "My Birth Chart"
    
    # Create NatalSet with inline location fields copied from Place
    place = request.user.default_place
    try:
        NatalSet.objects.create(
            name=name,
            owner=request.user,
            birth_datetime=birth_datetime,
            location_name=place.name,
            latitude=place.latitude,
            longitude=place.longitude,
            timezone=place.timezone,
            permission=NatalSet.Permission.PRIVATE
        )
    except Exception:
        return render(request, 'core/wizard_step2.html', {
            'place': place,
            'timezone': place.timezone,
            'error': 'Failed to save birth chart. Please try again.'
        })
    
    # Generate chart-of-now and return the partial
    from natal.clients import ChartRequest, generate_chart, ChartAPIError
    
    chart_request = ChartRequest(
        latitude=float(place.latitude),
        longitude=float(place.longitude),
        datetime=timezone.now(),
        format='svg'
    )
    
    context = {}
    try:
        chart = generate_chart(chart_request)
        context['chart'] = chart
    except ChartAPIError as e:
        context['error'] = str(e)
    
    return render(request, 'core/chart_of_now.html', context)


@require_POST
@login_required
def wizard_skip(request):
    """
    POST handler for skipping the wizard.
    
    Sets onboarding_dismissed_at to current time and returns:
    - chart-of-now partial if default_place is set
    - Empty/minimal content if no default_place
    """
    user = request.user
    user.onboarding_dismissed_at = timezone.now()
    user.save(update_fields=['onboarding_dismissed_at'])
    
    if user.default_place:
        # Return chart-of-now partial
        from natal.clients import ChartRequest, generate_chart, ChartAPIError
        
        place = user.default_place
        chart_request = ChartRequest(
            latitude=float(place.latitude),
            longitude=float(place.longitude),
            datetime=timezone.now(),
            format='svg'
        )
        
        context = {}
        try:
            chart = generate_chart(chart_request)
            context['chart'] = chart
        except ChartAPIError as e:
            context['error'] = str(e)
        
        return render(request, 'core/chart_of_now.html', context)
    else:
        # Return empty content for the chart area
        return HttpResponse('<div id="chart-of-now-widget" class="chart-placeholder"></div>')
