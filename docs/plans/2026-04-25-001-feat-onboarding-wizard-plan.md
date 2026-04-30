---
title: "feat: Guided Onboarding Wizard"
type: feat
status: completed
date: 2026-04-25
origin: docs/brainstorms/2026-04-24-onboarding-wizard-requirements.md
---

# feat: Guided Onboarding Wizard

## Overview

Add an inline 2-step onboarding wizard to the homepage that replaces the chart-of-now area for authenticated users who have no `default_place` and haven't previously dismissed the wizard. Step 1 captures location (browser geolocation or place search). Step 2 captures birth datetime and optional name, creating a NatalSet. The wizard is skippable at every step and does not reappear after dismissal.

***

## Problem Frame

New users who sign in via Google OAuth land on a blank homepage — `default_place` is null so no chart renders and no NatalSet exists. The data models are wired but there's no UI to populate them. This is the #1 activation gap. (See origin: `docs/brainstorms/2026-04-24-onboarding-wizard-requirements.md`)

***

## Requirements Trace

* R1. Wizard renders when authenticated user's `default_place` is null AND `onboarding_dismissed_at` is null. All POST endpoints require authentication; owner fields derived server-side from `request.user`.

* R2. When `default_place` is set, the wizard never appears — chart-of-now renders normally.

* R3. Step 1 offers browser geolocation button + existing place search widget for location input.

* R3a. Geolocation lat/long is reverse-geocoded server-side via Photon API reverse endpoint. On failure, inline error directs user to search.

* R3b. When geolocation is denied/unavailable/times out, inline message shown; search widget remains usable.

* R4. On location selection, Place is created (or reused by name+user) and set as `User.default_place`. Auto-advance to step 2. Timezone fallback via secondary lookup if geocoding returns null timezone.

* R5. Step 2 captures birth datetime + optional name. Timezone auto-derived from Place. NatalSet created with inline location fields copied from Place. Wizard completes, chart-of-now renders via HTMX.

* R6. Each step has visible Skip. Skip step 1 → sets `onboarding_dismissed_at`, saves nothing. Skip step 2 → keeps `default_place`, no NatalSet, sets `onboarding_dismissed_at`.

* R7. No follow-up nudge after dismissal. Wizard does not reappear while `onboarding_dismissed_at` is set.

**Origin actors:** User, Browser Geolocation API
**Origin flows:** F1 (first-time user completes onboarding), F2 (user skips), F3 (returning user with missing default\_place)

***

## Scope Boundaries

* No profile or account settings page — wizard is the only way to set `default_place` in this milestone

* No nudge or re-prompt system

* No modification to Google OAuth flow or allauth adapter

* No guest/anonymous onboarding — authenticated users only

* No chart preferences (house system, zodiac type)

* No new geocoding UI for manual entry — reuses existing `LocationAutocomplete` JS widget

### Deferred to Follow-Up Work

* Profile/settings page for managing `default_place` after wizard dismissal: future milestone

* Timezone API service for secondary lookup when Photon returns no timezone: implementation will determine if a lightweight HTTP call to a timezone API is needed

***

## Success Criteria

(From origin: `docs/brainstorms/2026-04-24-onboarding-wizard-requirements.md`)

* **Under 60 seconds from sign-in to personalized chart:** New Google OAuth user can go from "just signed in" to "seeing my personalized chart-of-now" in under 60 seconds. Verified by: integration test in U6 covering the full F1 flow, plus manual stopwatch check.

* **Works identically on mobile and desktop:** Wizard is responsive and functional on both. Verified by: manual browser testing during U4/U5; structural test scenarios ensure correct HTML form elements and HTMX attributes are present regardless of viewport.

* **Skipping does not break existing homepage:** Skipping the wizard does not break any existing homepage functionality. Verified by: U6 integration tests for skip paths (F2) confirming homepage remains usable.

* **Implementable without inventing behavior:** This plan has enough detail to implement without inventing user-facing behavior. Satisfied by: detailed requirements trace, test scenarios, and explicit decision records.

***

## Context & Research

### Relevant Code and Patterns

* **Homepage:** `core/views.py` — `home()` function-based view, conditionally calls `generate_chart()` when `request.user.default_place` is set. Template at `templates/core/home.html` wraps chart-of-now in `{% if user.is_authenticated and user.default_place %}` block.

* **Chart-of-now HTMX:** `core/views.py` — `chart_of_now()` returns `core/chart_of_now.html` partial. Triggered by `hx-get` on refresh button and `chart-of-now.js` idle timer.

* **Place model:** `natal/models.py` — `Place(name, latitude, longitude, timezone, created_by)` with unique constraint on `(name, created_by)`.

* **NatalSet model:** `natal/models.py` — `NatalSet(owner, birth_datetime, location_name, latitude, longitude, timezone, ...)` — stores location inline, not via FK to Place.

* **Forms:** `natal/forms.py` — `PlaceCreateForm` pops `user` from kwargs, sets `created_by`. `NatalSetCreateForm` pops `user`, sets `owner`, handles M2M. Pattern: `ModelForm.__init__` pops user, `save()` sets ownership.

* **Geocoding:** `natal/clients.py` — `geocode_location(query)` calls Photon forward search, returns list of `GeocodingResult`. No reverse geocoding exists.

* **Place search JS:** `static/js/location-autocomplete.js` — `LocationAutocomplete` class, constructor takes `{searchInput, onSelect}`. Self-contained, no dependencies. Debounced fetch to `/natal/api/location/search/`.

* **HTMX patterns:** CSRF token added globally via `htmx:configRequest` in `base.html`. Partials are standalone HTML fragments (no `{% extends %}`). `django-htmx` middleware adds `request.htmx`.

* **Auth:** `django-allauth` with Google OAuth. `SOCIALACCOUNT_AUTO_SIGNUP = True`, `LOGIN_REDIRECT_URL = '/'`. Custom adapters in `users/adapters.py`.

* **Testing:** `pytest-django` with `django.test.TestCase`. Mocking via `unittest.mock.patch`. HTMX tests use `HTTP_HX_REQUEST='true'` header. No factory pattern — objects created inline in `setUp()`.

### Institutional Learnings

No `docs/solutions/` directory exists. No institutional learnings captured yet for this project.

### External References

* Photon API reverse geocoding: `https://photon.komoot.io/reverse/?lon=...&lat=...` — same API, different endpoint from existing forward search.

***

## Key Technical Decisions

* **No wizard resumption after step 1:** If user completes step 1 (default\_place set) but navigates away before step 2, the wizard won't reappear — R2 applies. Users can create NatalSets via existing CRUD later. This avoids adding an `onboarding_step` state variable. (See origin: R1, R2)

* **Place reuse without coordinate update:** When the unique constraint `(name, created_by)` matches an existing Place, reuse it with original coordinates. No overwriting. The Place represents a named location, not exact position.

* **HTMX response strategy for wizard completion:** Step 2 POST generates chart data inline and returns the chart-of-now partial HTML, swapping `innerHTML` of the wizard container. Single request, no redirect, no secondary trigger.

* **Birth datetime timezone handling:** `datetime-local` input is interpreted as local time in the Place's IANA timezone. Stored as timezone-aware datetime using `zoneinfo.ZoneInfo(place.timezone)`. This is critical for correct natal chart calculation.

* **Timezone failure = hard block:** If reverse geocoding produces no timezone and secondary lookup also fails, Place creation fails with an error. No UTC fallback — incorrect timezone produces wrong charts.

* **Inline HTML partials for wizard steps:** Each wizard step is a standalone HTML fragment (like `chart_of_now.html`), not a full page. HTMX swaps the `#onboarding-wizard` container content between steps.

* **No persistent geolocation denial detection:** The geolocation button is always shown. Any failure (denied, unavailable, timeout) produces the same inline error message directing user to search.

***

## Open Questions

### Resolved During Planning

* **How does browser geolocation become a Place?** New `reverse_geocode_location(lat, lon)` function in `natal/clients.py` using Photon's `/reverse/` endpoint. Pattern follows existing `geocode_location()`.

* **NatalSet vs Place location data flow?** NatalSet stores location inline (no FK to Place). Place data must be explicitly copied into NatalSet fields when creating it.

* **Can LocationAutocomplete be embedded in wizard?** Yes — it's a self-contained JS class that takes a CSS selector and `onSelect` callback. Instantiate in wizard template with callback that populates hidden fields and triggers form submission.

* **HTMX swap strategy after wizard completion?** Step 2 POST returns chart-of-now partial directly, swapping `innerHTML` of wizard container. Single request.

* **What if user completes step 1 but leaves before step 2?** No resumption. R2 applies — chart-of-now renders. User can create NatalSet via CRUD later.

### Deferred to Implementation

* **Exact HTML structure and CSS for wizard UI:** The plan specifies what the wizard contains, not pixel-perfect layouts. The implementer should follow existing form styling patterns from `natal_set_form.html`.

* **Secondary timezone lookup implementation:** If Photon reverse geocoding returns no timezone, the implementer should evaluate options (e.g., `timezonefinder` library, another API) and choose the lightest-weight approach. This is a runtime decision.

* **Geolocation timeout value:** The browser Geolocation API accepts a timeout parameter. Choose a reasonable default during implementation (likely 10-15 seconds).

***

## Implementation Units

* [ ] U1. **Add** **`onboarding_dismissed_at`** **field to User model**

**Goal:** Add the field that gates wizard visibility and supports the dismissal mechanism.

**Requirements:** R1, R6, R7

**Dependencies:** None

**Files:**

* Modify: `users/models.py`

* Create: `users/migrations/XXXX_add_onboarding_dismissed_at.py`

* Test: `users/tests.py`

**Approach:**
Add `onboarding_dismissed_at = models.DateTimeField(null=True, blank=True)` to the User model. Create and apply migration. No default value — `null` means the wizard should show.

**Patterns to follow:**

* Existing `default_place` field pattern in `users/models.py`

* Standard Django migration workflow

**Test scenarios:**

* Happy path: Field exists on User model, defaults to None for new users

* Edge case: Existing users have null `onboarding_dismissed_at` after migration

* Happy path: Field can be set and cleared via ORM

**Verification:**

* Migration applies cleanly on existing database

* User model has the new field accessible via `user.onboarding_dismissed_at`

***

* [ ] U2. **Build reverse geocoding client function**

**Goal:** Add server-side reverse geocoding capability to convert browser lat/long into a Place with name and timezone.

**Requirements:** R3a, R4

**Dependencies:** None

**Files:**

* Modify: `natal/clients.py`

* Test: `natal/tests.py`

**Approach:**
Add `reverse_geocode_location(lat, lon)` function in `natal/clients.py` that calls Photon API's `/reverse/` endpoint (`GET https://photon.komoot.io/reverse/?lon={lon}&lat={lat}`). Return a `GeocodingResult` (reuse existing dataclass) with name, latitude, longitude, timezone. Handle the case where Photon returns no results or no timezone — return `None` for timezone, let caller decide fallback.

**Patterns to follow:**

* Existing `geocode_location()` function in `natal/clients.py` — same HTTP client pattern, same error handling, same `GeocodingResult` return type

* Existing `GeocodingRequest` / `GeocodingResult` dataclasses

**Test scenarios:**

* Happy path: Valid lat/lon returns GeocodingResult with name, lat, lon, timezone

* Edge case: Lat/lon in ocean/remote area returns empty results — function returns None or empty result

* Error path: Photon API returns non-200 — function raises appropriate exception

* Error path: Network timeout — function raises exception matching existing pattern

* Edge case: Photon returns result but no timezone — GeocodingResult has timezone=None

**Verification:**

* `reverse_geocode_location(40.7128, -74.0060)` returns a result with name containing "New York"

* Unit tests pass with mocked Photon API responses

***

* [ ] U3. **Create wizard views and URL endpoints**

**Goal:** Add the server-side views and URL routes for the onboarding wizard: render step 1, process step 1 (save Place), render step 2, process step 2 (save NatalSet), and handle skip/dismiss.

**Requirements:** R1, R3, R3a, R3b, R4, R5, R6, R7

**Dependencies:** U1, U2

**Files:**

* Create: `core/wizard.py` (or add to `core/views.py` — implementer decides based on size)

* Modify: `core/urls.py`

* Test: `core/tests.py`

**Approach:**

Create function-based views (matching existing `core/views.py` style) for:

1. **`wizard_step1`** (GET): Returns step 1 HTML partial (location input). Rendered inside `home()` when wizard conditions are met.
2. **`wizard_step1_submit`** (POST): Accepts location data from either geolocation or search. For geolocation: call `reverse_geocode_location(lat, lon)`, then create/reuse Place. For search: create/reuse Place from search result data. Set `User.default_place`. Return step 2 HTML partial via HTMX swap. On reverse-geocoding failure or timezone failure, return step 1 with inline error.
3. **`wizard_step2`** (GET): Returns step 2 HTML partial (birth datetime input). Display timezone from Place for confirmation.
4. **`wizard_step2_submit`** (POST): Validate birth datetime. Create NatalSet with inline location fields copied from `request.user.default_place`. Generate chart. Return chart-of-now partial HTML (swapping wizard container). On completion, `onboarding_dismissed_at` is NOT set — user has a complete setup.
5. **`wizard_skip`** (POST): Sets `User.onboarding_dismissed_at = timezone.now()`. Returns appropriate response: if `default_place` is set, return chart-of-now partial; if not, return empty/minimal content for the chart area.

All POST views require `request.user.is_authenticated`. All derive owner/created\_by from `request.user`. All return HTML partials for HTMX consumption.

**Technical design:**

```
Wizard flow (HTMX swaps on #onboarding-wizard):

home() view:
  if authenticated AND default_place is None AND onboarding_dismissed_at is None:
    render home.html with wizard_step1 partial in chart-of-now area
  elif authenticated AND default_place is set:
    render chart-of-now as normal
  else:
    render home.html without chart or wizard

wizard_step1_submit POST:
  geolocation path: JS sends {lat, lon} → server reverse-geocodes → create/reuse Place → set default_place → return step2 partial
  search path: LocationAutocomplete onSelect fills hidden fields → form submit → create/reuse Place → set default_place → return step2 partial
  error path: return step1 partial with inline error message

wizard_step2_submit POST:
  validate datetime → get default_place → copy Place fields into NatalSet → create NatalSet → generate chart → return chart-of-now partial

wizard_skip POST:
  set onboarding_dismissed_at → return chart-of-now partial (if default_place) or empty (if not)
```

**Patterns to follow:**

* Function-based views in `core/views.py` — `home()`, `chart_of_now()`

* `PlaceCreateForm` pattern: pop user from kwargs, set `created_by` on save

* `NatalSetCreateForm` pattern: pop user, set `owner`, copy inline location fields

* `generate_chart()` call from `core/views.py` for chart generation

* HTMX partial response pattern: return standalone HTML fragment (no `{% extends %}`)

**Test scenarios:**

* Happy path: Authenticated user with no default\_place and no dismissal sees wizard in homepage response

* Happy path: Authenticated user with default\_place set does NOT see wizard — chart-of-now renders (R2)

* Happy path: Authenticated user with onboarding\_dismissed\_at set does NOT see wizard (R7)

* Happy path: Anonymous user never sees wizard

* Integration: Step 1 submit with search data creates Place and sets default\_place, returns step 2 partial

* Integration: Step 1 submit with geolocation data calls reverse\_geocode\_location, creates Place, sets default\_place

* Error path: Step 1 geolocation fails reverse geocoding — returns step 1 with inline error (R3a)

* Error path: Step 1 geolocation returns no timezone and fallback fails — returns step 1 with inline error

* Happy path: Step 2 submit creates NatalSet with correct inline location fields from Place

* Happy path: Step 2 submit generates chart and returns chart-of-now partial

* Edge case: Step 2 submit with no name uses default "My Birth Chart"

* Happy path: Skip on step 1 sets onboarding\_dismissed\_at, saves nothing (R6)

* Happy path: Skip on step 2 sets onboarding\_dismissed\_at, keeps default\_place, no NatalSet (R6)

* Integration: After step 2 completion, chart-of-now renders with correct Place and NatalSet data

* Error path: Unauthenticated POST to any wizard endpoint returns 403 or redirects to login

* Edge case: Place already exists for user+name — reuses existing Place (R4)

**Verification:**

* All wizard endpoints return correct HTML partials

* Authenticated users without default\_place see wizard on homepage

* Authenticated users with default\_place or dismissed wizard see chart-of-now or no wizard

* Place creation and NatalSet creation work end-to-end

***

* [ ] U4. **Create wizard templates**

**Goal:** Build the HTML templates for both wizard steps, the skip mechanism, and integrate into the homepage.

**Requirements:** R3, R3b, R5, R6

**Dependencies:** U3

**Files:**

* Create: `templates/core/wizard_step1.html`

* Create: `templates/core/wizard_step2.html`

* Modify: `templates/core/home.html`

**Approach:**

**`wizard_step1.html`** — Standalone HTML partial (no `{% extends %}`). Contains:

* "Use my current location" button with JS geolocation handler

* Location search input with `LocationAutocomplete` instantiation

* Hidden form fields for lat, lon, timezone, location\_name (populated by geolocation or search)

* Skip button that POSTs to `wizard_skip`

* Inline error message area (hidden by default)

* Loading indicator for async operations

* Form `hx-post` to `wizard_step1_submit` with `hx-target="#onboarding-wizard"` and `hx-swap="innerHTML"`

**`wizard_step2.html`** — Standalone HTML partial. Contains:

* `<input type="datetime-local">` for birth datetime

* Optional name/label text input

* Timezone display (derived from Place, shown as read-only confirmation)

* Hidden fields for Place reference

* Skip button that POSTs to `wizard_skip`

* Submit button that POSTs to `wizard_step2_submit` with `hx-target="#onboarding-wizard"` and `hx-swap="innerHTML"`

**`home.html`** **modification:** Replace the current `{% if user.is_authenticated and user.default_place %}` block to add an `{% elif %}` branch: when `user.is_authenticated and not user.default_place and not user.onboarding_dismissed_at`, render a `<div id="onboarding-wizard">` containing `{% include "core/wizard_step1.html" %}`.

**Patterns to follow:**

* `templates/core/chart_of_now.html` — standalone partial pattern

* `templates/natal/natal_set_form.html` — form styling, `LocationAutocomplete` inclusion pattern, inline `<style>` blocks

* `templates/base.html` — CSRF token handling via `htmx:configRequest`

* Existing `class="form-control"` widget styling, `class="btn"` button styling

**Test scenarios:**

* Happy path: Step 1 partial contains geolocation button, search input, skip button, and hidden fields for lat/lon/timezone/location\_name

* Happy path: Step 2 partial contains datetime-local input, name input, timezone display, skip button, and submit button

* Happy path: Step 1 form has correct HTMX attributes (`hx-post`, `hx-target="#onboarding-wizard"`, `hx-swap="innerHTML"`)

* Happy path: Step 2 form has correct HTMX attributes targeting `#onboarding-wizard`

* Edge case: Homepage `{% elif %}` branch renders `<div id="onboarding-wizard">` with step 1 partial for eligible users

**Verification:**

* Wizard renders correctly on homepage for eligible users

* Step 1 partial includes geolocation button, search input, skip button

* Step 2 partial includes datetime input, name input, timezone display, skip and submit buttons

* HTMX attributes correctly target `#onboarding-wizard` container

***

* [ ] U5. **Add client-side JavaScript for geolocation flow**

**Goal:** Wire the browser Geolocation API to the step 1 form, handling success, failure, and loading states.

**Requirements:** R3, R3a, R3b

**Dependencies:** U4

**Files:**

* Create: `static/js/onboarding-wizard.js`

* Modify: `templates/core/wizard_step1.html` (include the JS)

**Approach:**

Create a small JS module that:

1. Listens for click on the "Use my current location" button
2. Calls `navigator.geolocation.getCurrentPosition()` with a reasonable timeout (10-15s)
3. On success: populates hidden form fields (lat, lon) and submits the form via HTMX (`htmx.trigger(form, 'submit')`)
4. On error (denied, unavailable, timeout): shows inline error message ("Location unavailable — please search manually") and ensures search widget is fully usable
5. Shows loading state on button during geolocation request

The `LocationAutocomplete` widget is already self-contained. Its `onSelect` callback will populate the same hidden fields and trigger form submission. Both input methods converge on the same hidden-field-then-submit pattern.

**Patterns to follow:**

* `static/js/chart-of-now.js` — vanilla JS, no build step, simple IIFE or module pattern

* `static/js/location-autocomplete.js` — vanilla JS class pattern

* Existing inline `<script>` blocks in templates for instantiation

**Test scenarios:**

* Happy path: Geolocation success fills hidden fields and submits form

* Error path: Geolocation denied shows inline error, search widget still works

* Error path: Geolocation timeout shows inline error

* Edge case: Button shows loading state during geolocation request

* Integration: Both geolocation and search paths submit the same form with correct hidden field values

**Verification:**

* Geolocation button triggers browser location prompt

* On allow: form submits with lat/lon hidden fields populated

* On deny: error message appears, search widget functional

* Loading state visible during geolocation

***

* [ ] U6. **Wire homepage conditional logic and integration tests**

**Goal:** Update the homepage view to render the wizard when conditions are met, and add end-to-end integration tests for the complete wizard flow.

**Requirements:** R1, R2, R6, R7

**Dependencies:** U1, U3, U4, U5

**Files:**

* Modify: `core/views.py`

* Test: `core/tests.py`

**Approach:**

Update `home()` in `core/views.py` to add the wizard trigger logic:

* If `request.user.is_authenticated` and `request.user.default_place is None` and `request.user.onboarding_dismissed_at is None`: render home.html with wizard step 1 included

* Otherwise: existing behavior (chart-of-now if default\_place, no chart if anonymous)

The template already handles the conditional via the `{% elif %}` branch from U4. The view just needs to ensure the template context is correct.

Add integration tests covering the full user journey from sign-in through wizard completion.

**Patterns to follow:**

* Existing `home()` view pattern in `core/views.py`

* Existing `ChartOfNowTest` class pattern in `core/tests.py`

* HTMX test pattern: `HTTP_HX_REQUEST='true'` header

**Test scenarios:**

* Integration: New Google OAuth user → homepage shows wizard → complete both steps → chart-of-now renders (F1)

* Integration: User skips step 1 → wizard dismissed, no default\_place, homepage sparse (F2)

* Integration: User completes step 1, skips step 2 → default\_place set, no NatalSet, chart-of-now renders (F2)

* Integration: User who previously dismissed sees no wizard on return (F3, R7)

* Integration: Returning user with no default\_place and no dismissal sees wizard (F3)

* Happy path: Existing user with default\_place never sees wizard (R2)

* Happy path: Anonymous user never sees wizard

* Integration: `generate_chart()` returns correct data immediately after wizard step 2 sets `default_place` and creates NatalSet in the same request cycle (validates origin assumption about no caching/stale-data)

**Verification:**

* Full integration test suite passes

* Homepage correctly shows wizard, chart-of-now, or empty state based on user state

* No regression in existing chart-of-now functionality for users with default\_place

***

## System-Wide Impact

* **Interaction graph:** The wizard adds 5 new URL endpoints under `core/`. The homepage `home()` view gains additional conditional logic. No existing endpoints are modified.

* **Error propagation:** Reverse geocoding failures propagate as inline error messages in the wizard (not server error pages). Geolocation failures are client-side only.

* **State lifecycle risks:** After step 1 completes, `default_place` is set but `onboarding_dismissed_at` is still null. If the user navigates away, they get chart-of-now without a NatalSet — this is accepted behavior, not a bug. No partial-write risk since each step is a single atomic transaction (create Place + set default\_place, or create NatalSet).

* **Integration coverage:** U3 and U6 tests cover the cross-layer interactions (view → client → model → template). The existing `generate_chart()` function is called by the wizard step 2 completion, verified by integration tests.

* **Unchanged invariants:** Existing NatalSet CRUD views, chart views, Place search endpoint, and allauth authentication flow are not modified. The wizard only adds new endpoints and a new conditional branch in the homepage view.

***

## Risks & Dependencies

| Risk                                                                                          | Mitigation                                                                                                                                                                                                                                                                                        |
| :-------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Photon reverse geocoding returns no timezone, blocking Place creation                         | Fallback to secondary timezone lookup (implementation-time choice). If both fail, show error and direct user to manual search where forward geocoding may return timezone.                                                                                                                        |
| Geolocation denied by most users, making step 1 feel broken                                   | Search widget is always available as primary fallback. Geolocation button is clearly optional ("Use my current location" label).                                                                                                                                                                  |
| `chart-of-now.js` doesn't rebind after HTMX swap                                              | The chart-of-now refresh button uses self-contained `hx-get` attributes — no JS rebinding needed. The idle timer in chart-of-now\.js uses `htmx.ajax()` which should work with swapped content. Verify during implementation.                                                                     |
| Place uniqueness constraint blocks legitimate use (same city name, different intent)          | Accepted — the constraint deduplicates by name per user. Users can create Places with different search terms (e.g., "Brooklyn, NY" vs "Manhattan, NY").                                                                                                                                           |
| `generate_chart()` returns stale data when `default_place` is freshly set in the same request | Origin assumption to verify. Mitigation: U6 integration test explicitly asserts chart data is correct immediately after wizard step 2 sets default\_place and creates NatalSet in the same request cycle. If caching is detected, add `refresh_from_db()` or clear cache before chart generation. |

***

## Sources & References

* **Origin document:** [docs/brainstorms/2026-04-24-onboarding-wizard-requirements.md](docs/brainstorms/2026-04-24-onboarding-wizard-requirements.md)

* Homepage view: `core/views.py`

* Chart-of-now template: `templates/core/chart_of_now.html`

* Place/NatalSet models: `natal/models.py`

* Geocoding client: `natal/clients.py`

* Location autocomplete JS: `static/js/location-autocomplete.js`

* Form patterns: `natal/forms.py`
