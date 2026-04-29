/**
 * Onboarding Wizard Geolocation Module
 * 
 * Handles browser geolocation for the onboarding wizard step 1.
 * - Detects user's location via navigator.geolocation
 * - Populates hidden form fields
 * - Triggers form submission via HTMX
 * - Handles errors gracefully with fallback to search
 */
(function() {
    // Geolocation timeout in milliseconds (10 seconds)
    const GEOLOCATION_TIMEOUT = 10000;

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', initOnboardingWizard);

    // Also listen for HTMX swap events (in case wizard is loaded dynamically)
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        if (evt.detail.target.id === 'onboarding-wizard') {
            initOnboardingWizard();
        }
    });

    function initOnboardingWizard() {
        const geolocationBtn = document.getElementById('wizard-geolocation-btn');
        const searchInput = document.getElementById('wizard-location-search');
        const errorDiv = document.getElementById('wizard-geolocation-error');

        if (!geolocationBtn) return;

        // Bind geolocation button click
        geolocationBtn.addEventListener('click', handleGeolocationClick);

        // Initialize location autocomplete if search input exists
        if (searchInput && typeof LocationAutocomplete !== 'undefined') {
            initLocationAutocomplete(searchInput);
        }
    }

    function initLocationAutocomplete(searchInput) {
        const autocomplete = new LocationAutocomplete({
            searchInput: '#wizard-location-search',
            onSelect: function(location) {
                // Populate hidden fields
                document.getElementById('wizard-lat').value = location.lat;
                document.getElementById('wizard-lon').value = location.lon;
                document.getElementById('wizard-timezone').value = location.timezone || '';
                document.getElementById('wizard-location-name').value = location.name;

                // Clear the search input (name is now in hidden field)
                searchInput.value = '';

                // Trigger form submission via HTMX
                const form = searchInput.closest('form');
                if (form) {
                    htmx.trigger(form, 'submit');
                }
            }
        });
    }

    function handleGeolocationClick(evt) {
        const btn = evt.currentTarget;
        const errorDiv = document.getElementById('wizard-geolocation-error');

        // Hide any previous error
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }

        // Check if geolocation is supported
        if (!navigator.geolocation) {
            showGeolocationError('Geolocation is not supported by your browser. Please use the search box below.');
            return;
        }

        // Show loading state
        btn.classList.add('loading');
        btn.disabled = true;

        // Request geolocation
        navigator.geolocation.getCurrentPosition(
            // Success callback
            function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                // Populate hidden fields
                document.getElementById('wizard-lat').value = lat;
                document.getElementById('wizard-lon').value = lon;

                // Note: timezone will be determined server-side via reverse geocoding
                document.getElementById('wizard-timezone').value = '';
                document.getElementById('wizard-location-name').value = '';

                // Trigger form submission via HTMX
                const form = btn.closest('form');
                if (form) {
                    htmx.trigger(form, 'submit');
                }
            },
            // Error callback
            function(error) {
                // Remove loading state
                btn.classList.remove('loading');
                btn.disabled = false;

                let errorMessage = 'Unable to detect your location. Please use the search box below.';

                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = 'Location access was denied. Please use the search box below.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = 'Location information is unavailable. Please use the search box below.';
                        break;
                    case error.TIMEOUT:
                        errorMessage = 'Location request timed out. Please use the search box below.';
                        break;
                }

                showGeolocationError(errorMessage);
            },
            // Options
            {
                enableHighAccuracy: false,
                timeout: GEOLOCATION_TIMEOUT,
                maximumAge: 300000 // 5 minutes cache
            }
        );
    }

    function showGeolocationError(message) {
        const errorDiv = document.getElementById('wizard-geolocation-error');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
})();
