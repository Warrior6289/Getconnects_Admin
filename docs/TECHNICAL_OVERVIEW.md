# Getconnects Admin – Technical Documentation

This document provides an in-depth look at the Getconnects Admin Flask application, including the runtime architecture, data model, integrations, and operational procedures. It is intended as a companion to the project README for developers and operators who need to understand how the system works end-to-end.

## Table of contents
1. [Technology stack and entry points](#technology-stack-and-entry-points)
2. [Configuration and environment](#configuration-and-environment)
3. [Application architecture](#application-architecture)
4. [Feature walkthrough and key functions](#feature-walkthrough-and-key-functions)
5. [Data model](#data-model)
6. [Services and business logic](#services-and-business-logic)
7. [Authentication and authorization flow](#authentication-and-authorization-flow)
8. [External integrations](#external-integrations)
9. [Command-line utilities and migrations](#command-line-utilities-and-migrations)
10. [Testing strategy](#testing-strategy)
11. [Development workflow tips](#development-workflow-tips)

## Technology stack and entry points

- **Framework:** Flask with the application factory pattern (`getconnects_admin.create_app`). The factory loads environment variables, applies configuration objects, initialises CSRF protection, caching, and ensures database prerequisites before registering blueprints.【F:getconnects_admin/__init__.py†L8-L109】
- **WSGI entry point:** `wsgi.py` imports the factory and creates the app using the `FLASK_CONFIG` environment variable, defaulting to production.【F:wsgi.py†L1-L5】
- **Templating:** Jinja2 templates live in `templates/`, while static assets live under `static/`.
- **ORM:** SQLAlchemy with declarative models. Engine and session configuration happen in `getconnects_admin/models/__init__.py`, supporting PostgreSQL and SQLite URLs with Supabase-specific validation.【F:getconnects_admin/models/__init__.py†L1-L52】
- **Forms:** WTForms powered via Flask-WTF in `getconnects_admin/forms.py` for client and lead management workflows.【F:getconnects_admin/forms.py†L1-L68】

## Configuration and environment

The application reads configuration from environment variables and dedicated config classes:

- `FLASK_SECRET_KEY` and `ENCRYPTION_KEY` (production) are mandatory for secure sessions and cryptographic operations.【F:getconnects_admin/__init__.py†L46-L59】
- `DATABASE_URL` accepts PostgreSQL (including Supabase) or SQLite URLs. Legacy `postgres://` prefixes are normalised and Supabase pooler connections are validated for the required `options=project=<ref>` parameter.【F:getconnects_admin/models/__init__.py†L19-L45】
- Supabase credentials (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`) power authentication and login flows.【F:getconnects_admin/services/auth_service.py†L12-L44】
- Optional integrations rely on `JUSTCALL_*`, Gmail (`GMAIL_*`), and SMTP environment variables for outbound notifications.【F:getconnects_admin/services/sms_service.py†L1-L68】【F:getconnects_admin/services/email_service.py†L1-L51】【F:getconnects_admin/services/auth_service.py†L46-L77】
- Configuration classes (`DevelopmentConfig`, `TestingConfig`, `ProductionConfig`) inherit from `BaseConfig` to toggle debugging, testing, and CSRF options.【F:getconnects_admin/config.py†L1-L26】

## Application architecture

### Factory lifecycle

1. Environment variables are loaded via `python-dotenv` to support `.env` files during local development.【F:getconnects_admin/__init__.py†L8-L28】
2. The Flask app is created with explicit template/static directories and configured using the selected config class.【F:getconnects_admin/__init__.py†L30-L57】
3. CSRF protection, in-memory caching, and a minimal database extension placeholder are initialised.【F:getconnects_admin/__init__.py†L60-L83】
4. `ensure_lead_type_tables` performs idempotent database bootstrapping so older deployments with legacy table names continue to work.【F:getconnects_admin/__init__.py†L84-L86】【F:getconnects_admin/db_bootstrap.py†L1-L64】
5. Global context processors expose helper functions (e.g., `has_permission`) to templates, while `before_request` enforces login requirements except for public endpoints and webhook routes.【F:getconnects_admin/__init__.py†L88-L134】
6. Blueprints covering authentication, dashboard, clients, campaigns, settings, statistics, pages, root, webhooks, and notifications are registered. The webhook blueprint is exempted from CSRF checks for third-party callbacks.【F:getconnects_admin/__init__.py†L136-L152】
7. A Flask CLI command `create-superuser` is registered to bootstrap privileged accounts.【F:getconnects_admin/__init__.py†L154-L196】

### Blueprint overview

| Blueprint | Module | Purpose |
| --- | --- | --- |
| `auth_bp` | `routes/auth.py` | Login/logout endpoints, Supabase JWT session exchange, and password reset UI.【F:getconnects_admin/routes/auth.py†L1-L72】 |
| `dashboard_bp` | `routes/dashboard.py` | Dashboard landing page showing aggregate stats and recent clients.【F:getconnects_admin/routes/dashboard.py†L1-L19】 |
| `clients_bp` | `routes/clients.py` | Client CRUD, management of lead type notification settings, JSON API exposure.【F:getconnects_admin/routes/clients.py†L1-L122】 |
| `campaigns_bp` | `routes/campaigns.py` | Campaign listing, client assignments, JustCall sync, and lead type group associations.【F:getconnects_admin/routes/campaigns.py†L1-L108】 |
| `settings_bp` | `routes/settings.py` | Administrative settings for JustCall credentials, Gmail SMTP, notification templates, and staff permissions.【F:getconnects_admin/routes/settings.py†L1-L130】 |
| `stats_bp` | `routes/stats.py` | (See module) exposes statistics endpoints for charts and reporting. |
| `pages_bp` & `root_bp` | `routes/pages.py`, `routes/__init__.py` | Static pages and root redirections. |
| `webhooks_bp` | `routes/webhooks.py` | Receives JustCall webhook payloads, maps JSON fields, and persists campaigns/leads accordingly.【F:getconnects_admin/routes/webhooks.py†L1-L161】【F:getconnects_admin/routes/webhooks.py†L162-L235】 |
| `notifications_bp` | `routes/notifications.py` | JSON and HTML views over notification logs for debugging delivery issues.【F:getconnects_admin/routes/notifications.py†L1-L51】 |

## Feature walkthrough and key functions

The following sections outline how user-facing features are assembled from routes, forms, services, and templates. Each walkthrough calls out notable helpers and implementation complexities to consider during maintenance or extension.

### Authentication and session lifecycle

1. Users land on `/login`, rendered by `login_page`, which retrieves Supabase configuration and missing key diagnostics for template hints.【F:getconnects_admin/routes/auth.py†L12-L33】
2. The client posts a Supabase ID token to `/sessionLogin`; `session_login` validates the token, provisions a user record if necessary, and stores permission flags within the Flask session.【F:getconnects_admin/routes/auth.py†L35-L63】
3. The global `require_login` hook redirects unauthenticated requests and refreshes user state on each request to ensure permission accuracy.【F:getconnects_admin/__init__.py†L81-L133】
4. Staff can be elevated through the CLI-only `create_superuser` command, which reuses the SQLAlchemy session factory for idempotent promotion flows.【F:getconnects_admin/__init__.py†L123-L196】

**Complexities:** Supabase tokens expire quickly; failures default to console logs, so production deployments should aggregate stderr. Session hydration mirrors database permissions exactly, making the `_user_permissions` cache critical for performance.【F:getconnects_admin/services/auth_decorators.py†L24-L63】

### Client and campaign administration

1. The clients dashboard renders `ClientForm` for inline creation and invokes `list_clients` to populate existing records.【F:getconnects_admin/forms.py†L9-L26】【F:getconnects_admin/services/client_service.py†L11-L55】
2. `create_client` and `delete_client` encapsulate transaction management and flash messaging, so route handlers simply branch on boolean return values.【F:getconnects_admin/services/client_service.py†L26-L80】
3. Campaign pages call `list_campaigns`, which joins `CampaignLeadTypeGroup` associations to surface linked JustCall dispositions without issuing N+1 queries.【F:getconnects_admin/services/campaign_service.py†L12-L36】
4. Manual sync flows delegate to `sync_campaigns` within the JustCall service to upsert campaigns and lead types atomically, respecting webhook-triggered updates.【F:getconnects_admin/services/justcall_service.py†L1-L109】

**Complexities:** Client deletion cascades through SQLAlchemy relationships, so soft-delete requirements would need additional guard rails. Campaign sync operations depend on remote API health; the service normalises identifiers to maintain referential integrity across webhook payloads.【F:getconnects_admin/routes/campaigns.py†L1-L108】

### Lead intake and notification pipeline

1. Leads can be created manually through `LeadForm` or programmatically via webhooks/import jobs. Both flows call `create_lead` to persist records and orchestrate notifications.【F:getconnects_admin/forms.py†L21-L83】【F:getconnects_admin/services/lead_service.py†L79-L276】
2. `_render_template` enriches template context with lead/client fields, `_strip_html` generates plaintext fallbacks, and the notification block inside `create_lead` routes to SMS/email helpers while logging outcomes.【F:getconnects_admin/services/lead_service.py†L36-L236】
3. Notification senders rely on secure credential storage; `JustCallCredential` and `GmailCredential` transparently encrypt secrets at rest while exposing decrypted accessors to channel services.【F:getconnects_admin/models/justcall_credential.py†L10-L49】【F:getconnects_admin/models/gmail_credential.py†L13-L51】【F:getconnects_admin/services/sms_service.py†L1-L118】【F:getconnects_admin/services/email_service.py†L1-L63】
4. `NotificationLog` entries capture rendered content, delivery status, and error messages, enabling the notifications view to present historical delivery attempts.【F:getconnects_admin/models/notification_log.py†L9-L24】【F:getconnects_admin/routes/notifications.py†L1-L51】

**Complexities:** Template rendering tolerates missing fields to avoid crashing webhook ingestion. Email delivery falls back to console output when SMTP is unavailable, but production deployments should configure Gmail credentials to avoid silent failures. SMS delivery adheres to JustCall rate limits; retries should respect provider guidelines to prevent throttling.

### Settings and credential management

1. The settings blueprint exposes forms to manage JustCall, Gmail, staff permissions, and notification templates, backed by service helpers that encrypt secrets and validate inputs.【F:getconnects_admin/routes/settings.py†L1-L130】
2. Credential setters write encrypted payloads via model property setters, ensuring secrets never persist in plaintext once `ENCRYPTION_KEY` is configured.【F:getconnects_admin/models/justcall_credential.py†L35-L49】【F:getconnects_admin/models/gmail_credential.py†L33-L51】
3. Staff management pages leverage `PAGE_OPTIONS` to assign granular permissions, updating `PagePermission` rows referenced by decorators at runtime.【F:getconnects_admin/services/auth_decorators.py†L11-L63】【F:getconnects_admin/models/page_permission.py†L9-L20】

**Complexities:** Because encryption keys live in environment variables, rotations require re-encrypting stored secrets. Provide a maintenance window when changing `ENCRYPTION_KEY` to avoid breaking credential access.

### Webhook ingestion and data synchronisation

1. JustCall webhooks post to routes registered under `webhooks_bp`; handlers validate shared tokens, load stored mappings, and translate payloads into lead/campaign updates.【F:getconnects_admin/routes/webhooks.py†L1-L235】
2. `JustCallWebhookPayload` persists raw payloads for auditing, while service helpers deduplicate updates based on campaign IDs and timestamps.【F:getconnects_admin/models/justcall_webhook_payload.py†L9-L24】【F:getconnects_admin/services/justcall_service.py†L69-L109】
3. Bootstrap logic (`ensure_lead_type_tables`) runs during app startup so legacy installations with old table names continue to ingest new webhook fields seamlessly.【F:getconnects_admin/db_bootstrap.py†L54-L99】

**Complexities:** Mapping definitions allow administrators to restrict which fields may be updated; webhook handlers drop unknown keys to prevent arbitrary writes. Ensure webhook tokens remain secret to guard against spoofed payloads.

### Reporting and analytics

1. Dashboard views call `get_stats` and `get_leads_by_campaign` to compute aggregate metrics for widgets and charts.【F:getconnects_admin/routes/dashboard.py†L1-L19】【F:getconnects_admin/services/stats_service.py†L1-L53】
2. Pagination helpers in `lead_service` keep statistics endpoints responsive by limiting row counts and deferring expensive sorting to the database layer.【F:getconnects_admin/services/lead_service.py†L150-L195】

**Complexities:** Aggregations rely on SQL functions; for large datasets add database indexes on `Lead.created_at`, `campaign_id`, and `client_id` to maintain responsiveness. Consider materialised views when trend reporting expands.

### Templating and static assets

- HTML templates in `templates/` implement the branded GetConnects UI with Bootstrap-based styling.
- Static assets such as CSS, JavaScript, and images are organised under `static/`.

## Data model

The SQLAlchemy models define the relational schema. Key entities include:

| Model | Table | Highlights |
| --- | --- | --- |
| `User` | `users` | Identified by Supabase UID; tracks staff/superuser flags and per-page permissions.【F:getconnects_admin/models/user.py†L1-L22】 |
| `PagePermission` | `page_permissions` | Associates users with allowed page paths consumed by access decorators.【F:getconnects_admin/models/page_permission.py†L1-L20】 |
| `Client` | `clients` | Business customers with contact details and relationships to leads and campaigns.【F:getconnects_admin/models/client.py†L1-L25】 |
| `Campaign` | `campaigns` | Dialer campaigns (string IDs) optionally linked to clients and lead types. |
| `Lead` | `leads` | Captured prospects with contact info, campaign/client foreign keys, and metadata such as disposition and caller details.【F:getconnects_admin/models/lead.py†L1-L27】 |
| `LeadType` & `LeadTypeGroup` | `lead_types`, `lead_type_groups` | Categorise dispositions synced from JustCall for routing notifications. |
| `ClientLeadTypeSetting` | `client_lead_type_settings` | Stores per-client toggles and template selections for each lead type. |
| `NotificationTemplate` | `notification_templates` | Named SMS/email templates with optional default designation.【F:getconnects_admin/models/notification_template.py†L1-L18】 |
| `NotificationLog` | `notification_logs` | Audits notification attempts with channel, status, and rendered message snapshot.【F:getconnects_admin/models/notification_log.py†L1-L20】 |
| `JustCallCredential` & `JustCallWebhook` | `justcall_credentials`, `justcall_webhooks` | Persist API credentials and webhook tokens/mappings for JustCall integration. |
| `GmailCredential` | `gmail_credentials` | Optional storage for Gmail SMTP access used by the email service. |

The database session helper `get_session()` centralises session lifecycle management for service modules.【F:getconnects_admin/services/helpers.py†L1-L24】

### Relational considerations and performance tuning

- **Foreign keys and cascading rules:** Relationships between `Client`, `Lead`, and `Campaign` default to SQLAlchemy's passive deletes. Alembic migrations should mirror these relationships with explicit `ON DELETE` clauses if you add hard database-level cascades.【F:getconnects_admin/models/client.py†L9-L26】【F:getconnects_admin/models/lead.py†L9-L34】
- **Encryption at rest:** Secret-bearing models store encrypted fields using Fernet; a missing `ENCRYPTION_KEY` disables encryption transparently but should be avoided outside development environments.【F:getconnects_admin/models/justcall_credential.py†L10-L49】【F:getconnects_admin/models/gmail_credential.py†L13-L51】
- **Row-level security migrations:** `ensure_lead_type_tables` renames both tables and associated PostgreSQL policies, which is essential when Supabase RLS is enabled. Run bootstrap scripts after each deployment targeting Supabase-hosted databases.【F:getconnects_admin/db_bootstrap.py†L54-L99】
- **Index strategy:** Time-series queries benefit from indexes on `leads.created_at`, `notification_logs.created_at`, and `campaign_lead_types.campaign_id`. Add composite indexes when introducing new filters (e.g., status + created_at) to keep `_query_leads` efficient.【F:getconnects_admin/services/lead_service.py†L90-L195】【F:getconnects_admin/models/notification_log.py†L9-L24】
- **Data retention:** Notification logs and webhook payloads can grow quickly. Implement scheduled pruning or archival strategies when storage becomes a concern.

## Services and business logic

### Authentication service

- `verify_supabase_token` validates Supabase JWTs, returning subject and email claims used to create or update user records during login.【F:getconnects_admin/services/auth_service.py†L24-L44】
- `supabase_config` exposes public keys for the front-end, listing missing environment variables for diagnostics.【F:getconnects_admin/services/auth_service.py†L46-L54】
- `create_supabase_user` and `send_activation_email` provide administrative helpers for provisioning staff accounts via Supabase and sending recovery links through SMTP or console fallbacks.【F:getconnects_admin/services/auth_service.py†L56-L77】

### Client and campaign services

- `create_client`, `list_clients`, and `delete_client` manage CRUD operations with flash messaging on failure.【F:getconnects_admin/services/client_service.py†L1-L63】
- `list_campaigns`, `fetch_campaigns`, and `sync_campaigns` interface with the JustCall Sales Dialer API, synchronising campaign metadata, lead type groups, and dispositions in an idempotent fashion.【F:getconnects_admin/routes/campaigns.py†L1-L108】【F:getconnects_admin/services/justcall_service.py†L1-L109】

### Lead service and notifications

- `create_lead` persists new leads, automatically inherits the client from the associated campaign, and orchestrates notification delivery across SMS and email. It renders templates with lead/client fields, records outcomes in `NotificationLog`, and surfaces warnings when credentials are missing.【F:getconnects_admin/services/lead_service.py†L79-L276】
- `list_leads`/`list_leads_paginated`, `update_lead`, `delete_lead`, and `bulk_delete_leads` provide filtered retrieval and maintenance helpers for lead records.【F:getconnects_admin/services/lead_service.py†L41-L78】【F:getconnects_admin/services/lead_service.py†L277-L360】

### Stats service

- `get_stats` computes aggregate counts for clients, campaigns, and leads, including week-to-date lead creation counts for dashboard widgets.【F:getconnects_admin/services/stats_service.py†L1-L33】
- `get_leads_by_campaign` exposes grouped lead totals to power charts and reports.【F:getconnects_admin/services/stats_service.py†L36-L53】

### Notification channels

- `send_sms` and `fetch_sms_numbers` in `sms_service` use stored or environment-provided JustCall credentials to send SMS and enumerate available sender numbers, gracefully logging failures.【F:getconnects_admin/services/sms_service.py†L1-L118】
- `send_email` in `email_service` retrieves Gmail credentials (database or environment/secret store) to deliver notifications via SMTP with optional HTML parts.【F:getconnects_admin/services/email_service.py†L1-L63】

## Authentication and authorization flow

1. Users authenticate through Supabase; the front-end exchanges the Supabase JWT with `/sessionLogin`. The backend verifies the token, creates or updates the user record, and hydrates the Flask session with permission flags.【F:getconnects_admin/routes/auth.py†L27-L64】
2. A `before_request` hook enforces authentication for non-public routes and redirects authenticated users away from the login page.【F:getconnects_admin/__init__.py†L94-L133】
3. Route decorators enforce fine-grained permissions:
   - `require_page` matches the current path (normalising `/api/*` endpoints) against stored page permissions or defaults for superusers/testing.【F:getconnects_admin/services/auth_decorators.py†L9-L63】
   - `require_staff` and `require_superuser` check session flags and lazily refresh from the database to gate administrative routes.【F:getconnects_admin/services/auth_decorators.py†L65-L109】
4. Page options are centrally defined for assignment via the staff management settings page.【F:getconnects_admin/services/auth_decorators.py†L9-L22】

## External integrations

- **Supabase:** Powers authentication and optional user provisioning/activation emails via the Supabase Admin API.【F:getconnects_admin/services/auth_service.py†L12-L77】
- **JustCall Sales Dialer:** Campaign synchronisation, webhook ingestion, and SMS delivery all rely on JustCall API credentials stored through the settings UI. Webhook payloads can be mapped to campaign or lead fields with safeguards against writing disallowed attributes.【F:getconnects_admin/services/justcall_service.py†L1-L109】【F:getconnects_admin/routes/webhooks.py†L1-L161】
- **Gmail SMTP:** Outbound email notifications can use stored Gmail credentials, including optional CC/BCC lists, to send templated lead alerts.【F:getconnects_admin/routes/settings.py†L64-L104】【F:getconnects_admin/services/email_service.py†L1-L63】 Ensure the Gmail account permits SMTP access (for example by enabling App Passwords or the workspace SMTP setting) so that message delivery succeeds during verification and runtime sends.
- **Notification Templates:** Administrators can store reusable SMS/email content and mark a default template consumed during lead notification dispatch.【F:getconnects_admin/models/notification_template.py†L1-L18】【F:getconnects_admin/services/lead_service.py†L132-L236】

## Command-line utilities and migrations

- Run database migrations with Alembic (`alembic upgrade head`) prior to starting the application; the bootstrap helper renames legacy tables when necessary to avoid runtime errors.【F:getconnects_admin/db_bootstrap.py†L1-L64】
- Use the `flask create-superuser` CLI command (with optional `--uid` and `--actor-email`) to promote initial or additional administrators while enforcing superuser approval rules.【F:getconnects_admin/__init__.py†L154-L196】

## Testing strategy

- The `tests/` directory contains a comprehensive pytest suite covering authentication, forms, service logic (email/SMS), webhook handling, permission enforcement, and settings flows. Fixtures in `tests/conftest.py` create isolated app instances using the testing configuration.
- Running `pytest` from the repository root executes the suite; CI and local developers should ensure the testing configuration is selected via `FLASK_CONFIG=testing` or the fixture defaults.

## Development workflow tips

1. Create and activate a virtual environment, then install dependencies with `pip install -r requirements.txt`.
2. Configure environment variables via `.env` for Supabase, database, and integration credentials as needed.
3. Apply migrations (`alembic upgrade head`) and launch the development server (`flask --app wsgi run` or `python -m flask run`).
4. Use the settings pages to store integration credentials and webhook mappings during manual testing.
5. Consult the notification logs page to debug delivery issues by inspecting recorded channel/status/message entries.【F:getconnects_admin/routes/notifications.py†L1-L51】
