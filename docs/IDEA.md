# Ancient Astrology Project Notes

## Base Idea

To build a set of useful APIs and tools for paying customers of https://ancient-astrology.com, a new website.

## Base Technology Stack

- Django
- PostgreSQL
- HTMX approach to site design
- oat.js or similar small CSS framework
- social login enabled
- astronomicon font, which has been also been decomposed to an SVG sprite-sheet for advanced presentation where needed.

## Primary Site Offerings

Site focuses on "Ancient" astrology, which uses the 7 classical planets, and whole-sign houses, along with custom
astrological metrics of use to practitioners of this style of Astrology.

### Natal

- users should have permissioned (self, named-groups, public) set of saved natal sets - a natal set being a name, date and place, with optional notes.
- charts can be generated for these natal sets on demand, using a backend API (which is a separate project already in beta Project, and its api will be given)
- in addition charts will be generated on demand for any arbitrary time/place.
- if a user sets a default place, then on the homepage is always a chart-of-now for that place, updated every 30 minutes on idle for a max of 12 hours.
- In addition to charts, site will present analysis details (not interpretations, but rather repeatable calculation results based on formulae) of the chart, along with hover-details.
- api for logged-in users to receive an SVG or PNG chart on demand

### Electional - enabled via a flag before presented on main site as this will be in a future phase.

- users will be able to query for "electional" astrological events using natural language.  This query will be passed to a backend LLM interface under development.
  - queries return a jobid
  - jobid request to api returns result or pending response
- saved queries for users, permissioned as above for natal sets.



