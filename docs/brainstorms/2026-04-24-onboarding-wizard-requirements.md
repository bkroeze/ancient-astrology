---
date: 2026-04-24
topic: onboarding-wizard
---

# Guided Onboarding Wizard

## Problem Frame

New users who sign in via Google OAuth land on a blank homepage — `default_place` is null, so no chart-of-now renders and no NatalSet exists. The data models are wired (`User.default_place` FK, `NatalSet` with birth data) but there is no UI to populate them. This is the #1 activation gap: users authenticate and immediately see nothing personalized.

---

## Key Flows

- F1. First-time user completes onboarding
  - **Trigger:** Authenticated user with `default_place=None` visits homepage
  - **Actors:** User, Browser Geolocation API
  - **Steps:** (1) Homepage replaces chart-of-now area with onboarding wizard. (2) User picks location via geolocation or place search. (3) Location saves as `default_place`. (4) User enters birth datetime + optional name. (5) NatalSet auto-created. (6) Wizard dismisses, chart-of-now renders via HTMX.
  - **Outcome:** User has `default_place` set and at least one NatalSet. Homepage shows personalized chart.
  - **Covered by:** R1, R3, R4, R5

- F2. User skips onboarding
  - **Trigger:** User clicks "Skip" on any wizard step
  - **Actors:** User
  - **Steps:** (1) User clicks skip. (2) Wizard dismisses. (3) Homepage state depends on skip point: skip on step 1 → no chart, unpersonalized; skip on step 2 (after completing step 1) → chart-of-now renders using default_place, no NatalSet exists.
  - **Outcome:** User's `default_place` is null (step 1 skip) or set with no NatalSet (step 2 skip). Homepage is usable.
  - **Covered by:** R6, R7

- F3. Returning user with missing default_place sees wizard
  - **Trigger:** Authenticated user (not brand new) with `default_place=None` visits homepage
  - **Actors:** User
  - **Steps:** Same wizard as F1 — no distinction between new and returning users.
  - **Outcome:** Same as F1 or F2 depending on completion.
  - **Covered by:** R1, R6, R7

---

## Requirements

**Wizard display and trigger**
- R1. When an authenticated user's `default_place` is null AND `onboarding_dismissed_at` is null, the homepage renders an inline onboarding wizard in place of the chart-of-now area. All wizard HTMX POST endpoints must require authentication (`LoginRequiredMixin` or equivalent); `Place.created_by`, `NatalSet.owner`, and `User.default_place` must be derived from `request.user` server-side, never from client-submitted form data.
- R2. When `default_place` is set, the wizard never appears — the chart-of-now renders normally.

**Step 1: Location**
- R3. Step 1 offers two location input methods: (a) "Use my current location" button using the browser Geolocation API, and (b) the existing place search widget for manual city/search entry.
- R3a. When geolocation is used, the browser's lat/long is sent to a server-side reverse-geocoding function (e.g., Photon API with lat/lon parameters) that returns a place name and timezone. If reverse-geocoding fails or returns no results, an inline error message is shown and the user is directed to use the search widget.
- R3b. When geolocation is denied, unavailable, or times out, an inline message (e.g., "Location unavailable — please search manually") is shown and the search widget remains fully usable.
- R4. On location selection, a `Place` record is created (or reused if one already exists for this user+name) and set as `User.default_place`. The wizard auto-advances to step 2. If the geocoding result lacks a timezone, a secondary timezone lookup (e.g., via lat/long → timezone API) is used as fallback before Place creation.

**Step 2: Birth data**
- R5. Step 2 captures birth datetime (date + time) and an optional name/label. If no name is provided, a default name is auto-generated (e.g., "My Birth Chart"). The timezone for the birth datetime is auto-derived from the Place selected in step 1 and displayed to the user for confirmation. On submission, a `NatalSet` is created with the birth data and the location from step 1 (the Place's lat/long/timezone/name are copied into the NatalSet's inline location fields). The wizard then completes and the chart-of-now renders immediately via HTMX.

**Skip and dismissal**
- R6. Each wizard step has a visible "Skip" option. Skipping on step 1 saves nothing, sets `User.onboarding_dismissed_at` to the current timestamp, and dismisses the wizard. Skipping on step 2 (after step 1 completed) keeps the `default_place` from step 1 but does not create a NatalSet. The wizard does not reappear while `onboarding_dismissed_at` is set.
- R7. No follow-up nudge, banner, or prompt appears after the wizard is dismissed. Users can later set their default_place through other routes (future profile/settings page). The `onboarding_dismissed_at` field can be cleared to re-trigger the wizard if needed.

---

## Success Criteria

- A new Google OAuth user can go from "just signed in" to "seeing my personalized chart-of-now" in under 60 seconds.
- The wizard works identically on mobile and desktop browsers.
- Skipping the wizard does not break any existing homepage functionality.
- Planning has enough detail to implement without inventing user-facing behavior.

---

## Scope Boundaries

- No profile or account settings page — the wizard is the only way to set default_place in this milestone.
- No "nudge" or re-prompt system for users who skip.
- No modification to the Google OAuth flow itself (no allauth adapter changes, no redirect to a separate onboarding URL).
- No guest/anonymous onboarding — this is for authenticated users only.
- No chart preferences (house system, zodiac type) — future work.
- No new geocoding UI for manual entry — the existing place search widget handles that. Browser geolocation reverse-geocoding is deferred to planning (see Outstanding Questions).

---

## Key Decisions

- **Inline on homepage, not separate page:** The wizard replaces the chart-of-now area on the homepage rather than redirecting to `/onboarding/`. This keeps the user on a familiar page and avoids adding a new URL/redirect flow.
- **Two-step, not three:** Location and birth data are the minimum needed for a working personalized homepage. Name/label on the NatalSet is optional.
- **Skippable at every step:** Forcing onboarding creates friction. Users who skip can still explore the app unpersonalized.
- **Browser geolocation as optional, not primary:** Many users will decline browser location permission. The existing place search widget is the reliable fallback.
- **Reuses existing Place model and search widget:** No new models or search infrastructure — just wiring existing components into the wizard flow.

---

## Dependencies / Assumptions

- The existing place search widget in `natal/` can be embedded in a new template context (unverified assumption — needs verification during planning).
- The browser Geolocation API returns coordinates that can be reverse-geocoded into a Place with timezone. The app may need a reverse-geocoding step if the existing place search widget doesn't handle raw lat/long input.
- `generate_chart()` in `core/views.py` works correctly when `default_place` is freshly set — no caching or stale-data issue.
- HTMX can swap the wizard out and the chart-of-now in without a full page reload.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R3][Technical] How does the browser geolocation result (lat/long) get turned into a Place with timezone? Does the existing place search widget accept raw coordinates, or does a new geocoding call need to be wired in?
- [Affects R5][Technical] Does the NatalSet need a `Place` FK, or does it store location inline (the model currently has inline lat/long/timezone fields)? Confirm during planning.
- [Affects R1][Needs research] Can the existing place search widget be used as an HTMX partial inside the wizard, or does it need to be adapted?

---

## Next Steps

-> `/ce-plan` for structured implementation planning
