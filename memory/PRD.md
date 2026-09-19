# CARGO | كارجو — Product Requirements & Progress

## Original Problem Statement
Clean architectural rebuild of Phase 1 of CARGO: a professional, connected, secure, bilingual
(Arabic default RTL + English LTR) logistics marketplace for Oman & the Middle East. ONE connected
platform (web now, mobile-ready architecture) where Customer → Shipment → Marketplace → Driver/Provider →
Bid → Acceptance → Trip → Tracking → Delivery → Rating → Admin monitoring, all on shared persistent data.

## Architecture
- **Backend**: FastAPI (modular: server.py, auth.py, models.py, database.py, seed.py), all routes under `/api`.
- **DB**: MongoDB (single source of truth). UUID string ids on all entities.
- **Auth**: JWT (Bearer token in localStorage `cargo_token`). Admin = email+password (bcrypt). Users = phone + Demo OTP.
  Role-based authorization via `require_roles()` dependency. Roles: customer, driver, provider, admin (+ provider company_role).
- **Frontend**: React 19 + react-router 7 + Tailwind + shadcn. Centralized i18n (`src/i18n`) with translation keys,
  persisted language (`cargo_lang`), dir switching on <html>. Leaflet + OpenStreetMap map (`MapPicker`) with Nominatim search + reverse geocode (coordinate fallback if geocoding blocked).
- **Design**: navy #16233A + orange #F1701E derived from CARGO logo. Cairo (AR) / Plus Jakarta Sans (EN).

## User Personas
Customer (shipper), Driver (individual carrier), Transport Provider (company), Admin (operator).

## Core Requirements (static)
Bilingual real i18n + RTL/LTR + persistence; 4 role portals + separate protected /admin; interactive map for
pickup+delivery with lat/lng/address; driver verification gating marketplace eligibility; bidding + acceptance →
trip; trip status progression + tracking; delivery confirmation + rating; admin dashboard/verification/shared data + audit log.

## Implemented (2026-06)
- Public landing page (hero, how-it-works, services, who-uses, contact) — AR/EN.
- OTP login (customer/driver/provider) with on-screen demo code; separate admin email/password login at /admin.
- Customer portal: home, my shipments, single-page simplified Create Shipment form (description + optional photo → pickup map → delivery map → combined date/time → 3 service checkboxes → live summary + Publish) with location validation, shipment detail with bid comparison, accept bid, live trip tracking, confirm delivery, rating, profile.
- Driver portal: home, verification banner + documents/vehicle submission, available shipments (approved-only), submit bid, my bids, active trip with status progression, trip history, profile.
- Provider portal: dashboard (opportunities + trips), profile.
- Admin portal: dashboard (real stats + recent activity), driver management with approve/reject/suspend/request-changes (+ audit log, marketplace eligibility effect), shipments, bids, trips, users, audit log tables.
- Notifications (connected, per-user) with bell dropdown.
- Seed: admin + demo customer/drivers(approved+pending)/provider + 2 published shipments.

## Testing (2026-06)
- Backend: 33/33 pytest passed (auth, OTP, verification gating, full connected flow, admin endpoints, authz 401/403, persistence). Suite: /app/backend/tests/test_cargo_backend.py.
- Frontend: language toggle+persistence, admin login/nav/logout-protection, customer & driver OTP flows, verification banner — all verified by testing agent.

## Update — 2026-02 (investor feedback: simplified Create Shipment UX)
- Rewrote `frontend/src/pages/customer/CreateShipment.jsx` from a 6-step wizard to a single-page scrolling form:
  1) one description textarea (`ship-title`) + optional single photo upload,
  2) pickup MapPicker (`section-from`), 3) delivery MapPicker (`section-to`),
  4) combined `When` (pickup date/time + delivery date/time),
  5) exactly 3 service checkboxes (fragile, loading_service, unloading_service),
  6) live summary card at bottom with a full-width **Publish** button (`publish-btn`).
- REMOVED: category selector, quantity/weight/dimensions, vehicle-type chooser, expected-price input, separate Review step, Next/Back wizard controls.
- Backend already accepted empty `vehicle_type` and `expected_price` (Optional str defaults). Frontend now posts them as `""`.
- Added Arabic + English i18n keys: simpleTitle, cargoPlaceholder, addPhotoOptional, fromTitle, toTitle, pickupWhen, deliveryWhen, servicesTitle, summary, selectedServices, noServices.
- Verified end-to-end by testing agent (iteration_2.json): 11/11 scenarios passed on both mobile 390x844 and desktop 1920x1080. POST /api/shipments returned 200 with empty vehicle/price; redirected to /customer/shipments with success toast.
- Route note: in-app create button routes to `/customer/create` (not `/customer/shipments/new`). All customer nav buttons already point there; users unaffected.

## Backlog (P1 — next)
- Document image/file upload (currently reference + expiry fields; needs object storage).
- Ratings history views, provider fleet/driver management & dispatch, reports.
- Disputes, richer notifications, demo reset.

## Future
Real SMS OTP provider, real payment gateway, real GPS tracking, advanced analytics, native iOS/Android apps (shared API already in place).

## Notes / Limitations
- Demo OTP only (no real SMS) — code returned in API response and shown on screen.
- Tracking is simulated (driver-updated status + events on the real Trip); no real GPS yet.
- Nominatim geocoding may be rate-limited from datacenter IPs; map falls back to click-to-place with lat/lng.
