---
date: 2026-04-24
topic: user-personalization
focus: User personalization and functionality — logged-in users having personalized experiences like "chart of now" using default lat/long, saved preferences, dashboards
mode: repo-grounded
---

# Ideation: User Personalization & Functionality

## Grounding Context

**Codebase:** Django 5.2 / Python astrology web app with HTMX, django-allauth (Google OAuth), DRF. Domain apps: core (homepage), natal (chart CRUD), electional (NL-query, flag-gated), jobs (async polling), users. Custom User model with `default_place` FK to `natal.Place` — wired but no UI. NatalSet model with full permissions (private/named\_group/public), sharing, notes — models built, views/templates missing. Chart-of-now on homepage partially working. No profile page, no dashboard, no saved charts management UI.

**External context:** Astro.com has "My Astro" storing 100 birth data entries, multi-person switching, "Chart of the Moment" widget. Co-Star uses real-time transit notifications. No competitor offers personalized daily transit dashboards grounded in real natal chart data. Weather app, fitness tracker, and personal finance dashboards provide strong cross-domain analogies.

## Ranked Ideas

### 1. Guided Onboarding Wizard (Post-OAuth)

**Description:** After Google OAuth, intercept with a 2-step wizard: (1) browser geolocation or city search to create default\_place, (2) birth datetime to auto-create first NatalSet. Both write to DB in one transaction, then redirect to a populated homepage with a working chart-of-now.
**Rationale:** Closes the #1 activation gap. default\_place FK is wired but has no UI. Users authenticate and get a blank homepage. Minimal new code needed — the data models and chart API already exist.
**Downsides:** Adds friction to the OAuth redirect flow — must be skippable for users who want to explore first.
**Confidence:** 92%
**Complexity:** Low
**Status:** Unexplored

### 2. Personal "Today" Dashboard

**Description:** A logged-in landing page showing: personal transit score, moon phase, exact aspects hitting natal planets, and "best windows today" mini-electional for common activities. Like Oura's "Readiness Score" but for astrology — "your astrological weather today."
**Rationale:** Combines existing data (default\_place, chart API, electional engine) into one high-value surface. No competitor does this with real natal data. Creates a daily habit loop — users return to check "their sky today."
**Downsides:** Requires transit-to-natal calculation pipeline that doesn't exist yet.
**Confidence:** 85%
**Complexity:** Medium
**Status:** Unexplored

### 3. Transit Overlay on Saved Charts ("Living Charts")

**Description:** Every saved natal chart renders with a toggle-able layer showing today's transits against natal positions. Charts are no longer static snapshots — they're natal patterns that the live sky is always interacting with.
**Rationale:** Makes saved charts worth revisiting daily. The generic comparison engine unlocks synastry, composite charts, progressions, and relocation later — classic compounding leverage.
**Downsides:** Needs a transit calculation endpoint or API integration.
**Confidence:** 80%
**Complexity:** Medium
**Status:** Unexplored

### 4. Progressive Onboarding Through Session Charts

**Description:** Unauthenticated users can create temporary charts (stored in session/localStorage) and see basic transit overlays. On login, these session charts are "claimed" into the user's permanent library. The app is fully usable without an account; the account adds persistence.
**Rationale:** Removes the biggest conversion barrier — users experience core value before committing. E-commerce "cart before checkout" pattern.
**Downsides:** Session-based storage layer needs design; migration on login must be atomic.
**Confidence:** 75%
**Complexity:** Medium
**Status:** Unexplored

### 5. Cosmic Readiness Score

**Description:** A single composite number (0-100) derived from how today's transiting planets interact with the user's natal chart — like Oura's Readiness Score. Displayed prominently on the homepage. "Today is a 73 — Mercury squares your Sun — expect communication friction."
**Rationale:** Most people can't read a wheel chart. A score makes transit data immediately actionable and shareable. Drives daily engagement with zero user effort.
**Downsides:** Scoring algorithm requires design and astrological validation. Simplification risks alienating serious practitioners.
**Confidence:** 70%
**Complexity:** Medium
**Status:** Unexplored

### 6. Annual Cosmic Retrospective

**Description:** A shareable, visually rich annual summary: "Your Saturn return began in March," "You had 47 transits to your natal Moon," "Your most intense week was October 12-18." Spotify Wrapped for astrology.
**Rationale:** Spotify Wrapped is the most successful viral marketing tool in consumer tech. Astrology is inherently about identity — an annual retrospective would have even higher shareability because it says something about who you are.
**Downsides:** Requires pre-computing a year of transit data. Best as a year-end feature; doesn't drive daily engagement the rest of the year.
**Confidence:** 65%
**Complexity:** High
**Status:** Unexplored

### 7. Collaborative Electional — Social Timing Events

**Description:** When creating a wedding/travel/group electional query, invite collaborators whose natal charts are factored into the timing analysis. The existing named\_group permission + shared\_with M2M infrastructure becomes a collaboration graph. All QueryType choices (WEDDING, PROJECT, TRAVEL, MOVE\_IN) are inherently multi-person.
**Rationale:** Electional is the app's unique differentiator. Making it social multiplies that differentiator. The permission infrastructure already exists.
**Downsides:** Electional itself is flag-gated with no UI yet — this builds on an unbuilt feature.
**Confidence:** 60%
**Complexity:** High
**Status:** Unexplored

## Rejection Summary

| #  | Idea                                        | Reason Rejected                                          |
| :- | :------------------------------------------ | :------------------------------------------------------- |
| 1  | User Profile Page                           | Duplicates stronger self-configuring homepage approach   |
| 2  | Never-Empty Form (autofill)                 | Too incremental — table stakes, not ideation-worthy      |
| 3  | Invisible Permissions (share links only)    | Discards existing named\_group infrastructure            |
| 4  | Dashboard-as-Inbox (notification feed)      | Too vague — no concrete notification triggers            |
| 5  | One-Click Chart (skip form)                 | Duplicates Quick Cast, less interesting                  |
| 6  | Chart-of-Now API Endpoint (SVG/PNG)         | Technical infrastructure, not personalization feature    |
| 7  | Activity Feed (cross-cutting log)           | Incremental action log, not a personalization hook       |
| 8  | Query Templates (parameterized SavedQuery)  | Premature — electional has no UI yet                     |
| 9  | Locational Astrology Map (astrocartography) | Niche, high-complexity — effectively a separate product  |
| 10 | Chart Notebook (standalone journal)         | Duplicates Chart Annotations Layer (better scoped)       |
| 11 | Real-Time Planetary Animation               | Visual polish, not personalization breakthrough          |
| 12 | Ambient Dashboard (full-screen, no menus)   | Impractical — discards standard web navigation           |
| 13 | Premium Personalization (paywall)           | Monetization strategy, not personalization feature       |
| 14 | Ephemeral Charts (auto-expiring)            | Contradicts app purpose — users want permanent charts    |
| 15 | Anonymous Session Charts                    | Duplicates Progressive Onboarding survivor               |
| 16 | Astrological Weather Public Homepage        | Duplicates Browser Geolocation for Guests                |
| 17 | Location Library (User.places M2M)          | Incremental data model tweak, not headline feature       |
| 18 | Shareable Chart Links (standalone)          | Subsumed by social platform combination                  |
| 19 | Transit Alert Notifications                 | Duplicates Transit Watch (same idea, different frame)    |
| 20 | Saved People & Quick Synastry               | Subsumed by Chart Household / comparison combos          |
| 21 | Silent Geolocation (kill coordinate field)  | Merged into Guided Onboarding and Progressive Onboarding |
| 22 | Self-Configuring Homepage (toast capture)   | Merged into Guided Onboarding survivor                   |
| 23 | Electional Auto-Journal                     | Merged into Collaborative Electional survivor            |
| 24 | Unified Temporal Query                      | Premature — requires electional UI first                 |
| 25 | Chart Comparison Infrastructure             | Subsumed by Living Charts (transit overlay) survivor     |
| 26 | Planetary Weather Strip (7-day)             | Subsumed by Personal Today Dashboard                     |
| 27 | Electional Trip Planner (calendar heatmap)  | Subsumed by Collaborative Electional                     |
| 28 | Browser Geolocation for Guests              | Merged into Progressive Onboarding                       |
| 29 | My Astro Dashboard (NatalSet card grid)     | Subsumed by Personal Today Dashboard                     |
| 30 | Chart Annotations Layer                     | Strong but lower priority than the 7 survivors           |
| 31 | UserPreferences Singleton Model             | Important infrastructure but not ideation-worthy         |
| 32 | Widget Grid Dashboard (per-user layout)     | Architecture decision, not a feature idea                |
| 33 | Personal Astrological Calendar              | Subsumed by Personal Today Dashboard                     |
| 34 | NatalSet Comparison / Synastry Quick View   | Subsumed by Living Charts and social combos              |
| 35 | Live Transit Strip (HTMX polling)           | Subsumed by Personal Today Dashboard                     |
| 36 | Quick Cast (arbitrary chart without saving) | Subsumed by Progressive Onboarding                       |
| 37 | Chart Household (multi-person management)   | Subsumed by Collaborative Electional and Living Charts   |
