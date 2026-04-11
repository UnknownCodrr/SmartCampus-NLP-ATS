# Changelog
All notable changes to the SmartCampus project are documented in this file.

## [v1.1.0-Beta] - 2026-04-10
### Added
- Implemented a "Zero-Trust" Invite-Only Architecture with a master toggle switch for Placement Coordinators.
- Added a secure email whitelist system to restrict account creation to pre-approved students only.
- Added the ability for coordinators to permanently delete broadcasted campus announcements from the dashboard.
- Introduced a Skill Normalization Layer (Alias Mapping) in the matching algorithm to accurately equate syntax variations (e.g., "react.js" and "react").

### Changed
- Refactored the `mega_skills.json` master database from a flat array into a structured dictionary (Core Tech vs. Managerial Skills) for enhanced maintainability.
- Updated the NLP Engine to dynamically flatten the categorized JSON dictionary at runtime for seamless resume scanning.

### Fixed
- Resolved a database mapping error (`coordinator_id`) that caused broadcasted announcements to fail silently on the frontend.

## [v1.0.0-Beta] - 2026-04-05
### Added
- Implemented pure-Python Single Page Application (SPA) routing via `st.navigation`.
- Added strict Domain Whitelisting to lock registrations to `@its.edu.in`.
- Integrated real-time database aggregation for live platform metrics on the login screen.
- Added Concurrent Session Management to prevent multi-device ghost logins.
- Applied Semantic Versioning (SemVer) with the release codename 'Genesis'.

## [v0.9.0-Alpha] - 2026-03-25
### Added
- Integrated Custom NLP Engine for resume parsing.
- Built the core SmartScore matching algorithm.
- Initialized MySQL database schema and authentication flows.
- Overall main web app was developed during this phase.