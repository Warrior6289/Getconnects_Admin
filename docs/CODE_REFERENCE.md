# Code Reference

This document provides a step-by-step walkthrough of every package, module, class, and function in the Getconnects Admin codebase. It is organised by directory so you can quickly locate implementation details while navigating the project.

## Repository layout

- `wsgi.py` – Imports :func:`getconnects_admin.create_app` and instantiates the Flask application for production servers. 【F:wsgi.py†L1-L5】
- `requirements.txt` / `requirements.lock` – Dependency pins for production and deterministic builds.
- `setup.cfg` – Tooling configuration (pytest, coverage, flake8).
- `migrations/` – Alembic version scripts for database migrations.
- `scripts/` – Helper scripts used by CI and development workflows.
- `static/` – Compiled assets (CSS, JS, images) served by Flask.
- `templates/` – Jinja templates rendered by the route handlers.
- `tests/` – Pytest suite covering application behaviour (see [Test suite](#test-suite)).
- `docs/TECHNICAL_OVERVIEW.md` – High-level architecture guide.
- `docs/CODE_REFERENCE.md` (this file) – Function-by-function documentation for the entire codebase.

## Feature deep dives

This section enumerates the critical functions for each major feature, showing how routes, services, forms, and templates collaborate.

### Authentication

- **Login page rendering:** `routes/auth.login_page` fetches Supabase settings and renders `templates/login.html` with missing-key diagnostics.【F:getconnects_admin/routes/auth.py†L12-L33】
- **Session creation:** `routes/auth.session_login` validates Supabase ID tokens, provisions a `User`, and hydrates the Flask session (`uid`, `user_id`, `is_staff`, `is_superuser`, `permissions`).【F:getconnects_admin/routes/auth.py†L35-L63】
- **Permission enforcement:** `services/auth_decorators.require_login` (within the factory) guards routes, while `require_page`, `require_staff`, and `require_superuser` enforce page-level permissions before view execution.【F:getconnects_admin/__init__.py†L81-L133】【F:getconnects_admin/services/auth_decorators.py†L24-L127】
- **CLI elevation:** `create_superuser` (registered by the factory) uses `SessionLocal` to upsert privileged users when bootstraping environments.【F:getconnects_admin/__init__.py†L123-L196】

### Client management

- **Listing:** `routes/clients.clients` queries `list_clients` to build the table payload and binds `ClientForm` for inline creation.【F:getconnects_admin/routes/clients.py†L19-L73】【F:getconnects_admin/services/client_service.py†L11-L55】
- **Creation:** `services/client_service.create_client` uses `SessionLocal` within a context manager, flashing `"Client created"` on success and rolling back on exceptions. `forms.ClientForm` validates emails and phone numbers before submission.【F:getconnects_admin/services/client_service.py†L26-L55】【F:getconnects_admin/forms.py†L9-L26】
- **Deletion:** `services/client_service.delete_client` removes records and cascaded relationships; the route responds with JSON for asynchronous UI updates.【F:getconnects_admin/routes/clients.py†L99-L122】【F:getconnects_admin/services/client_service.py†L57-L80】

### Campaign administration

- **Data retrieval:** `services/campaign_service.list_campaigns` composes campaign dictionaries with related client names and disposition group labels for template iteration.【F:getconnects_admin/services/campaign_service.py†L12-L36】
- **JustCall sync:** `routes/campaigns.sync_campaigns` posts to `services/justcall_service.sync_campaigns`, which fetches remote campaigns, ensures local `CampaignLeadTypeGroup` associations, and updates notification toggles atomically.【F:getconnects_admin/routes/campaigns.py†L49-L108】【F:getconnects_admin/services/justcall_service.py†L1-L109】
- **Association editing:** Blueprint actions invoke `CampaignLeadType` models and rely on the template to surface per-disposition checkboxes tied to JSON APIs under `/api/campaigns` (see route definitions for handlers).【F:getconnects_admin/models/campaign_lead_type.py†L9-L25】【F:getconnects_admin/routes/campaigns.py†L72-L108】

### Lead intake and lifecycle

- **Form/UI:** `forms.LeadForm` and `forms.LeadImportForm` supply manual entry and CSV import flows; `pages.leads_page` hydrates dynamic choices before rendering and routes submissions through the service layer.【F:getconnects_admin/forms.py†L21-L83】【F:getconnects_admin/routes/pages.py†L106-L339】
- **Creation:** `services/lead_service.create_lead` attaches the correct `Client` by campaign lookup, persists the `Lead`, renders templates via `_render_template`, strips HTML for SMS with `_strip_html`, and invokes channel helpers directly via `send_sms`/`send_email` while logging outcomes.【F:getconnects_admin/services/lead_service.py†L36-L360】【F:getconnects_admin/services/sms_service.py†L1-L118】【F:getconnects_admin/services/email_service.py†L1-L63】
- **Listing/filtering:** `_query_leads`, `list_leads`, and `list_leads_paginated` accept filters (client, campaign, lead type, date range) and return serialisable dictionaries for table or API responses consumed by HTML and CSV exports.【F:getconnects_admin/services/lead_service.py†L90-L195】【F:getconnects_admin/routes/pages.py†L198-L532】
- **Updates/deletes:** `update_lead`, `delete_lead`, `bulk_delete_leads`, and the import/report helpers back the management endpoints defined in `routes/pages.py`.【F:getconnects_admin/services/lead_service.py†L195-L360】【F:getconnects_admin/routes/pages.py†L224-L532】

### Notification management

- **Templates:** `models.NotificationTemplate` holds SMS/email content; settings routes offer create/update forms and mark defaults for reuse.【F:getconnects_admin/models/notification_template.py†L9-L22】【F:getconnects_admin/routes/settings.py†L35-L130】
- **Logs UI:** `routes/notifications.notifications` queries recent `NotificationLog` rows and renders them for debugging, while `/api/notifications` serves JSON for tooling integrations.【F:getconnects_admin/routes/notifications.py†L1-L51】【F:getconnects_admin/models/notification_log.py†L9-L24】
- **Credential storage:** `models.JustCallCredential` and `models.GmailCredential` expose encrypted property setters/getters powering the settings forms and notification services.【F:getconnects_admin/models/justcall_credential.py†L10-L49】【F:getconnects_admin/models/gmail_credential.py†L13-L51】

### Webhooks and external sync

- **Webhook registration:** `models.JustCallWebhook` stores target metadata; the settings UI can create tokens that map to campaign IDs or lead types.【F:getconnects_admin/models/justcall_webhook.py†L9-L26】【F:getconnects_admin/routes/settings.py†L88-L130】
- **Payload handling:** `routes/webhooks.handle_justcall_event` authenticates tokens, persists `JustCallWebhookPayload`, and branches into campaign or lead handlers. Helpers translate payload keys using stored mappings to prevent arbitrary attribute writes.【F:getconnects_admin/routes/webhooks.py†L1-L235】【F:getconnects_admin/models/justcall_webhook_payload.py†L9-L24】
- **Campaign refreshing:** `services/justcall_service.fetch_campaigns` and `sync_campaigns` interact with the JustCall API, normalising responses before merging into local tables. Idempotency is maintained via `CampaignLeadTypeGroup` association updates inside a transaction.【F:getconnects_admin/services/justcall_service.py†L1-L109】

### Reporting

- **Dashboard metrics:** `services/stats_service.get_stats` aggregates counts and week-to-date metrics for the dashboard blueprint, while `get_leads_by_campaign` generates grouped totals used by charts.【F:getconnects_admin/routes/dashboard.py†L1-L19】【F:getconnects_admin/services/stats_service.py†L1-L53】
- **Exports:** JSON endpoints under `routes/stats` serialise the metrics so BI tooling can reuse the data without duplicating aggregation logic.【F:getconnects_admin/routes/stats.py†L1-L75】

## Application package: `getconnects_admin`

### Module: `getconnects_admin/__init__.py`

- Globals
  - `csrf`: Flask-WTF CSRF protection extension initialised for the app factory. 【F:getconnects_admin/__init__.py†L32-L36】
  - `cache`: Flask-Caching instance configured with a simple backend. 【F:getconnects_admin/__init__.py†L32-L36】
  - `db`: Lightweight placeholder with `init_app` no-op to mimic Flask-SQLAlchemy style hooks. 【F:getconnects_admin/__init__.py†L38-L44】
- Functions
  - `create_app(config_name: str | None = None) -> Flask`: Application factory responsible for assembling the Flask app. Steps: load environment variables, instantiate `Flask` with template/static folders, select configuration class (defaults to development) and load it, validate `SECRET_KEY` and production-only `ENCRYPTION_KEY`, attach CSRF, cache, and dummy DB extensions, call `ensure_lead_type_tables` for backward compatibility, install a `context_processor` exposing `has_permission`, register `before_request` hook `require_login` to gate access based on the session, register all blueprints, exempt webhook blueprint from CSRF, add a 403 error handler, and define a `create-superuser` CLI command that promotes or creates a user with superuser privileges. Returns the configured app instance. 【F:getconnects_admin/__init__.py†L48-L157】
    - Nested `inject_permissions()` context processor defines helper `has_permission(path)` that checks session flags and stored permissions for templates. 【F:getconnects_admin/__init__.py†L64-L79】
    - Nested `require_login()` `before_request` hook redirects unauthenticated users to `/login` except for public endpoints and webhooks. 【F:getconnects_admin/__init__.py†L81-L109】
    - Nested CLI function `create_superuser(email, uid, actor_email)` enforces authorisation rules, upserts a user, flips `is_staff`/`is_superuser`, and persists the change. 【F:getconnects_admin/__init__.py†L123-L154】
- Re-exports: module exposes service helpers, ORM classes, SQLAlchemy session/engine and extensions via `__all__`. 【F:getconnects_admin/__init__.py†L160-L180】

### Module: `getconnects_admin/config.py`

- `BaseConfig`: Sets secure session cookie defaults and loads `SECRET_KEY` and `ENCRYPTION_KEY` from environment variables at instantiation. 【F:getconnects_admin/config.py†L1-L10】
- `DevelopmentConfig`: Enables Flask debug mode and loosens secure cookie flags for local development. 【F:getconnects_admin/config.py†L12-L16】
- `TestingConfig`: Enables testing mode, disables CSRF, and disables secure cookies to support test clients. 【F:getconnects_admin/config.py†L18-L22】
- `ProductionConfig`: Inherits defaults for production deployments. 【F:getconnects_admin/config.py†L24-L25】
- `config`: Mapping from config name to configuration class consumed by the app factory. 【F:getconnects_admin/config.py†L27-L30】

### Module: `getconnects_admin/db_bootstrap.py`

Utilities that ensure renamed lead-type tables exist for older deployments.

- `_schema_for(engine) -> str | None`: Detects the default schema for the SQLAlchemy engine (returns "public" for PostgreSQL). 【F:getconnects_admin/db_bootstrap.py†L11-L17】
- `_table_names(engine, schema) -> set[str]`: Returns a lower-cased set of table names for the given schema. 【F:getconnects_admin/db_bootstrap.py†L19-L24】
- `_policy_exists(engine, table, policy) -> bool`: Checks if a PostgreSQL row-level security policy exists for the named table. Performs a SQL query when using PostgreSQL and returns `False` otherwise. 【F:getconnects_admin/db_bootstrap.py†L26-L44】
- `_qualified(schema, identifier) -> str`: Helper that prefixes an identifier with the schema when provided. 【F:getconnects_admin/db_bootstrap.py†L46-L52】
- `ensure_lead_type_tables(engine) -> None`: Idempotent migration that renames legacy `client_dispositions` and `dispositions` tables (and their policies) to the new `client_lead_type_settings` and `lead_types` names. Uses transactional ALTER statements and suppresses policy rename failures. No-ops when `engine` is `None`. 【F:getconnects_admin/db_bootstrap.py†L54-L99】

### Module: `getconnects_admin/forms.py`

WTForms definitions used by HTML pages.

- `ClientForm(FlaskForm)`: Collects company name, contact info, email, and phone with validation. 【F:getconnects_admin/forms.py†L9-L18】
- `LeadForm(FlaskForm)`: Captures lead details including contact info, campaign, lead type, caller details, and notes. Select fields have dynamic choices populated at runtime. 【F:getconnects_admin/forms.py†L21-L41】
- `LeadImportForm(FlaskForm)`: CSV upload form capturing file input, column mappings, and consent checkbox for bulk import. Hidden/select fields store column names discovered during upload. 【F:getconnects_admin/forms.py†L44-L83】

### Package: `getconnects_admin/models`

`models/__init__.py` initialises SQLAlchemy and validates the database URL. 【F:getconnects_admin/models/__init__.py†L1-L40】
- Globals
  - `DATABASE_URL`: Normalised and validated database connection string supporting PostgreSQL and SQLite. Enforces Supabase pooler requirements. 【F:getconnects_admin/models/__init__.py†L17-L35】
  - `engine`: Shared SQLAlchemy engine created from `DATABASE_URL`. 【F:getconnects_admin/models/__init__.py†L37-L38】
  - `SessionLocal`: Session factory used across services and routes. 【F:getconnects_admin/models/__init__.py†L37-L39】
  - `Base`: Declarative base for ORM models. 【F:getconnects_admin/models/__init__.py†L41-L41】

Model classes (all inherit from `Base`):

- `User`: Represents application staff; columns include `uid`, `email`, optional names, and boolean `is_superuser`/`is_staff`. Defines `permissions` relationship to `PagePermission`. 【F:getconnects_admin/models/user.py†L9-L24】
- `Client`: Business customer with company, contact, email, phone, timestamp, and relationships to `Lead` and `Campaign`. 【F:getconnects_admin/models/client.py†L9-L26】
- `Campaign`: Marketing campaign keyed by string ID, storing name, status, owning client, and relationships to `Lead` and `CampaignLeadTypeGroup`. 【F:getconnects_admin/models/campaign.py†L9-L26】
- `Lead`: Captures inbound lead details (contact, lead type, caller metadata, notes, associations to client/campaign) and creation timestamp. 【F:getconnects_admin/models/lead.py†L9-L34】
- `LeadTypeGroup`: Group of lead types (`disposition_groups` table) with relationship to `LeadType`. 【F:getconnects_admin/models/lead_type_group.py†L9-L21】
- `LeadType`: Specific lead disposition linked to a `LeadTypeGroup`. 【F:getconnects_admin/models/lead_type.py†L9-L21】
- `CampaignLeadTypeGroup`: Association table linking campaigns to lead type groups. Composite primary key `(campaign_id, disposition_group_id)`. 【F:getconnects_admin/models/campaign_lead_type_group.py†L9-L25】
- `CampaignLeadType`: Association table linking campaigns to individual lead types with notification flags (`sms_enabled`, `email_enabled`). Composite primary key `(campaign_id, disposition_id)`. 【F:getconnects_admin/models/campaign_lead_type.py†L9-L25】
- `ClientLeadTypeSetting`: Stores per-client notification preferences and optional template reference for each lead type. 【F:getconnects_admin/models/client_lead_type_setting.py†L9-L31】
- `NotificationTemplate`: Named templates for notifications containing SMS text, email subject/body, and default flag. 【F:getconnects_admin/models/notification_template.py†L9-L22】
- `NotificationLog`: Audit log for notification attempts with relationships to `Client` and `Lead`. 【F:getconnects_admin/models/notification_log.py†L9-L24】
- `PagePermission`: Records accessible page paths for each user. 【F:getconnects_admin/models/page_permission.py†L9-L20】
- `JustCallCredential`: Stores encrypted JustCall API credentials and optional default SMS number. Property accessors transparently encrypt/decrypt values using `ENCRYPTION_KEY`. 【F:getconnects_admin/models/justcall_credential.py†L9-L43】
- `GmailCredential`: Stores encrypted Gmail SMTP credentials plus optional from/CC/BCC addresses with encrypting properties. 【F:getconnects_admin/models/gmail_credential.py†L9-L53】
- `JustCallWebhook`: Persists webhook tokens, target type, optional mapping JSON, and relationship to payload logs. 【F:getconnects_admin/models/justcall_webhook.py†L9-L26】
- `JustCallWebhookPayload`: Logs incoming webhook payloads with timestamp and relationship back to the webhook. 【F:getconnects_admin/models/justcall_webhook_payload.py†L9-L24】

### Package: `getconnects_admin/services`

#### Module: `services/helpers.py`
- `get_session()`: Context manager yielding a SQLAlchemy session created from `SessionLocal`, ensuring it is closed after use. 【F:getconnects_admin/services/helpers.py†L1-L19】

#### Module: `services/auth_service.py`
- `_get_supabase_client() -> Client`: Loads Supabase URL and key from environment, raises `ValueError` if missing, and initialises the Supabase Python client. 【F:getconnects_admin/services/auth_service.py†L8-L18】
- `verify_supabase_token(id_token) -> Optional[Dict[str, str]]`: Uses Supabase client to validate a JWT, returning a dict of subject/email claims or `None` on failure. 【F:getconnects_admin/services/auth_service.py†L20-L31】
- `supabase_config() -> tuple[dict, list[str]]`: Builds config dict for login templates and lists missing keys. 【F:getconnects_admin/services/auth_service.py†L33-L37】
- `create_supabase_user(email)`: Best-effort helper that invokes Supabase admin API to create a user, swallowing exceptions. 【F:getconnects_admin/services/auth_service.py†L39-L48】
- `send_activation_email(email)`: Generates a Supabase recovery link and either prints it (when SMTP unconfigured) or emails it via SMTP credentials stored in environment variables. Handles SMTP auth and logs fallback message on errors. 【F:getconnects_admin/services/auth_service.py†L50-L79】

#### Module: `services/auth_decorators.py`
- `PAGE_OPTIONS`: List of allowed page paths with human-readable labels used by staff management. 【F:getconnects_admin/services/auth_decorators.py†L11-L22】
- `_user_permissions() -> list[str]`: Retrieves cached permissions from the session, populates them from the database when absent, grants all when superuser or in testing, and stores them back into the session cache. 【F:getconnects_admin/services/auth_decorators.py†L24-L52】
- `require_page(view)`: Decorator enforcing page-level permissions; normalises `/api/*` routes to share page permissions and aborts with 403 when access is denied. 【F:getconnects_admin/services/auth_decorators.py†L54-L75】
- `require_staff(view)`: Decorator ensuring the user is staff or superuser; falls back to database lookup to refresh session flags. 【F:getconnects_admin/services/auth_decorators.py†L77-L104】
- `require_superuser(view)`: Decorator restricting endpoints to superusers, refreshing session flags as necessary. 【F:getconnects_admin/services/auth_decorators.py†L106-L127】

#### Module: `services/client_service.py`
- `list_clients() -> list[dict]`: Queries all `Client` rows and returns serialised dicts with metadata. 【F:getconnects_admin/services/client_service.py†L11-L24】
- `create_client(company_name, contact_name, contact_email, phone) -> bool`: Persists a new client inside a managed session, logging and flashing errors when persistence fails. 【F:getconnects_admin/services/client_service.py†L26-L55】
- `delete_client(client_id) -> bool`: Deletes a client by ID, flashing results and rolling back on errors. 【F:getconnects_admin/services/client_service.py†L57-L80】

#### Module: `services/campaign_service.py`
- `list_campaigns() -> list[dict]`: Builds a list of campaigns enriched with client names and associated lead type group names by joining through `CampaignLeadTypeGroup`. 【F:getconnects_admin/services/campaign_service.py†L12-L36】

#### Module: `services/lead_service.py`
- `_logger()`: Returns `current_app.logger` when available, otherwise module-level logger. 【F:getconnects_admin/services/lead_service.py†L28-L34】
- `_render_template(text, lead, client) -> str`: Formats template strings with fields from `Lead` and optional `Client`, adding derived `first_name`/`last_name` and prefixed client fields. Gracefully ignores formatting errors. 【F:getconnects_admin/services/lead_service.py†L36-L83】
- `_strip_html(html) -> str`: Removes HTML tags for plaintext email content. 【F:getconnects_admin/services/lead_service.py†L85-L88】
- `_query_leads(...)`: Internal helper constructing a filtered SQLAlchemy query based on client, campaign, lead type, and date range filters. 【F:getconnects_admin/services/lead_service.py†L90-L104】
- `list_leads(...) -> list[dict]`: Executes `_query_leads`, iterates over results, and serialises leads with related names. 【F:getconnects_admin/services/lead_service.py†L106-L148】
- `list_leads_paginated(...) -> tuple[list[dict], int]`: Applies pagination to `_query_leads`, returning serialised rows and total count. 【F:getconnects_admin/services/lead_service.py†L150-L195】
- `create_lead(...) -> tuple[bool, str | None]`: Inserts a lead, derives client association from campaign, commits, and orchestrates notification sending. Sends SMS/email when enabled via client settings or default template, logs results to `NotificationLog`, and surfaces warnings for missing credentials. Returns `(True, None)` on success, or `(False, error)` after rolling back on failure. 【F:getconnects_admin/services/lead_service.py†L197-L377】
- `update_lead(...) -> bool`: Updates persisted fields for an existing lead, reassigning client from campaign when provided. Rolls back and flashes on error. 【F:getconnects_admin/services/lead_service.py†L379-L428】
- `delete_lead(lead_id) -> bool`: Deletes a single lead safely with rollback and flash handling. 【F:getconnects_admin/services/lead_service.py†L430-L446】
- `bulk_delete_leads(lead_ids) -> int`: Deletes multiple leads using a set-based query, returning the count of deleted rows. Rolls back on errors. 【F:getconnects_admin/services/lead_service.py†L448-L471】

#### Module: `services/stats_service.py`
- `get_stats() -> dict`: Counts clients, campaigns, total leads, and leads created within the last 7 days. 【F:getconnects_admin/services/stats_service.py†L1-L33】
- `get_leads_by_campaign() -> list[dict]`: Performs outer join between campaigns and leads to return lead counts per campaign. 【F:getconnects_admin/services/stats_service.py†L35-L53】

#### Module: `services/sms_service.py`
- `_logger()`: Returns app logger when possible, falling back to module logger. 【F:getconnects_admin/services/sms_service.py†L18-L23】
- `send_sms(to_number, message, from_number=None) -> bool`: Loads JustCall credentials (preferring database entries), constructs payload, and POSTs to the JustCall SMS API. Returns `True` on HTTP success, logging and returning `False` otherwise. 【F:getconnects_admin/services/sms_service.py†L25-L71】
- `fetch_sms_numbers() -> list[str]`: Calls JustCall numbers API, normalises various response shapes, and returns a list of phone numbers formatted in E.164. Logs errors and returns an empty list when credentials missing or request fails. 【F:getconnects_admin/services/sms_service.py†L73-L134】

#### Module: `services/email_service.py`
- `_logger()`: Logger helper mirroring SMS service. 【F:getconnects_admin/services/email_service.py†L16-L21】
- `_get_env_credential(key)`: Retrieves credentials from environment or optional secret store plugin. 【F:getconnects_admin/services/email_service.py†L23-L34】
- `_get_db_credentials()`: Returns stored Gmail credentials if present. 【F:getconnects_admin/services/email_service.py†L36-L38】
- `send_email(to_email, subject, body, *, html=None) -> bool`: Builds an email message (including optional CC/BCC from stored credentials), connects to Gmail SMTP over SSL, sends the message, and returns success flag. Logs and returns `False` on failure or missing credentials. 【F:getconnects_admin/services/email_service.py†L40-L78】

#### Module: `services/justcall_service.py`
- Constants: `JUSTCALL_API_BASE` base URL, module-level `logger`. 【F:getconnects_admin/services/justcall_service.py†L25-L31】
- `fetch_campaigns(api_key, api_secret) -> list[dict]`: Performs authenticated GET request to JustCall Sales Dialer campaigns endpoint, returning the JSON `data` payload or `[]` on request failure. 【F:getconnects_admin/services/justcall_service.py†L33-L57】
- `sync_campaigns(campaigns)`: Iterates fetched campaign dictionaries and upserts `Campaign`, `LeadTypeGroup`, `LeadType`, `CampaignLeadTypeGroup`, and `CampaignLeadType` records, ensuring idempotent synchronisation and deduplicating groups/dispositions. Commits at the end. 【F:getconnects_admin/services/justcall_service.py†L59-L133】

### Package: `getconnects_admin/routes`

Each module defines a Flask blueprint and associated route handlers.

#### `routes/__init__.py`
- Imports individual blueprints and defines `root_bp` with `/` redirecting to `/dashboard`. 【F:getconnects_admin/routes/__init__.py†L1-L24】

#### `routes/auth.py`
- `login_page()`: GET `/login` renders login template unless user already authenticated. Injects Supabase config for frontend SDK. 【F:getconnects_admin/routes/auth.py†L10-L24】
- `reset_password_page()`: GET `/reset-password` renders password reset template with Supabase config. 【F:getconnects_admin/routes/auth.py†L26-L32】
- `session_login()`: POST `/sessionLogin` verifies Supabase JWT, creates/updates `User` entry, stores session fields (`uid`, `user_id`, flags, permissions), and returns 204 or 401. 【F:getconnects_admin/routes/auth.py†L34-L61】
- `logout()`: GET `/logout` clears the session and redirects to `/login`. 【F:getconnects_admin/routes/auth.py†L63-L69】

#### `routes/campaigns.py`
- `campaigns_page()`: GET `/campaigns` renders campaigns listing template (permission-protected). 【F:getconnects_admin/routes/campaigns.py†L24-L31】
- `campaigns_index()`: GET `/api/campaigns` returns JSON list via `list_campaigns`. 【F:getconnects_admin/routes/campaigns.py†L33-L37】
- `sync_campaigns_route()`: POST `/campaigns/sync` fetches stored JustCall credentials, attempts API sync, flashes status messages, and redirects back to listing. 【F:getconnects_admin/routes/campaigns.py†L39-L66】
- `manage_campaign(campaign_id)`: GET/POST `/campaigns/<id>` assigns client and lead type groups; POST updates associations, propagates client to existing leads, and flashes confirmation. GET populates templates with available clients/groups. 【F:getconnects_admin/routes/campaigns.py†L68-L115】

#### `routes/clients.py`
- `clients_page()`: GET/POST `/clients` renders clients template with form; POST validates form and creates client then redirects. 【F:getconnects_admin/routes/clients.py†L21-L38】
- `clients_index()`: GET `/api/clients` returns JSON list of clients. 【F:getconnects_admin/routes/clients.py†L40-L44】
- `manage_client(client_id)`: GET/POST `/clients/<id>/manage` edits client info and notification settings. Builds lead type listings from campaigns/groups, handles form submission to update `Client` fields and `ClientLeadTypeSetting` records, persists changes, and renders detailed template. 【F:getconnects_admin/routes/clients.py†L46-L131】
- `delete_client(client_id)`: POST `/clients/<id>/delete` deletes the client via service and flashes result. 【F:getconnects_admin/routes/clients.py†L133-L138】

#### `routes/dashboard.py`
- `dashboard_index()`: GET `/dashboard` renders dashboard template with client list and aggregated stats. 【F:getconnects_admin/routes/dashboard.py†L9-L18】

#### `routes/pages.py`
- `lead_types_page()`: GET `/lead-types` queries groups/lead types and renders overview. 【F:getconnects_admin/routes/pages.py†L33-L52】
- `manage_dispositions(group_id)`: GET/POST `/lead-types/<group_id>/manage` manages lead types within a group: POST handles deletions and additions (comma-separated names), GET renders details. 【F:getconnects_admin/routes/pages.py†L54-L103】
- `leads_page()`: GET/POST `/leads` handles filters, pagination, creation of leads via `LeadForm`, populates forms with campaign/lead type options, calls `list_leads_paginated`, and renders template with filter state. POST uses `create_lead` then redirects. 【F:getconnects_admin/routes/pages.py†L105-L199】
- `update_lead_route(lead_id)`: POST `/leads/<id>/update` validates form, updates lead via `update_lead`, and redirects back to list. 【F:getconnects_admin/routes/pages.py†L201-L225】
- `delete_lead_route(lead_id)`: POST `/leads/<id>/delete` removes a single lead. 【F:getconnects_admin/routes/pages.py†L227-L233】
- `bulk_delete_leads_route()`: POST `/leads/bulk-delete` mass deletes selected leads via `bulk_delete_leads`. 【F:getconnects_admin/routes/pages.py†L235-L244】
- `import_leads()`: POST `/leads/import` validates CSV upload, infers column mappings, ensures campaigns/lead types exist, creates leads via service, tracks successes/failures, flashes summary, and redirects. 【F:getconnects_admin/routes/pages.py†L246-L337】
- `report_options()`: GET `/leads/report/options` renders column-selection UI for exports. 【F:getconnects_admin/routes/pages.py†L339-L356】
- `leads_report()`: GET `/leads/report` collects filters/columns, fetches leads, writes CSV, and returns downloadable response. 【F:getconnects_admin/routes/pages.py†L358-L412】
- `settings_page()`: Placeholder route rendering a generic settings template (legacy). 【F:getconnects_admin/routes/pages.py†L414-L416】

#### `routes/settings.py`
- Helper functions `_notification_templates_supports_email_text`, `_load_legacy_notification_templates`, `_load_legacy_notification_template` detect schema support and fetch templates when migrations missing. 【F:getconnects_admin/routes/settings.py†L29-L94】
- `justcall_settings()`: GET/POST `/settings/justcall` manages stored JustCall credentials, webhook tokens, default numbers, and lists available SMS numbers. Handles actions for saving/deleting credentials and webhooks. 【F:getconnects_admin/routes/settings.py†L96-L162】
- `gmail_settings()`: GET/POST `/settings/gmail` manages encrypted Gmail SMTP credentials, including optional CC/BCC addresses. 【F:getconnects_admin/routes/settings.py†L164-L204】
- `notification_templates()`: GET/POST `/settings/templates` lists notification templates, enforces migration requirements, handles creation/deletion/default selection, and exposes placeholder fields for templates. 【F:getconnects_admin/routes/settings.py†L206-L279】
- `edit_notification_template(template_id)`: GET/POST `/settings/templates/<id>` edits an existing template, updating fields and default flag while respecting migration guard. 【F:getconnects_admin/routes/settings.py†L281-L338】
- `notification_test()`: GET/POST `/settings/notifications/test` sends test SMS or email messages using stored credentials. 【F:getconnects_admin/routes/settings.py†L340-L370】
- `justcall_webhook_detail(webhook_id)`: GET `/settings/justcall/<id>` renders detail page for a webhook token. 【F:getconnects_admin/routes/settings.py†L372-L381】
- `user_settings()`: GET/POST `/settings/users` manages staff accounts: adds users with roles/permissions, updates role assignments and page permissions, triggers Supabase provisioning, and renders user list. 【F:getconnects_admin/routes/settings.py†L383-L434】
- `profile()`: GET/POST `/settings/profile` lets logged-in user update their name fields. Redirects to login if session missing. 【F:getconnects_admin/routes/settings.py†L436-L457】

#### `routes/stats.py`
- `stats_index()`: GET `/stats` returns aggregate stats JSON. 【F:getconnects_admin/routes/stats.py†L7-L12】
- `stats_leads_by_campaign()`: GET `/stats/leads_by_campaign` returns campaign lead counts as JSON. 【F:getconnects_admin/routes/stats.py†L14-L17】

#### `routes/notifications.py`
- `notifications_index()`: GET `/notifications` returns recent notification log entries with related client/lead names. Accepts `limit` query parameter. 【F:getconnects_admin/routes/notifications.py†L8-L31】
- `notifications_all()`: GET `/notifications/all` renders template listing all logs. 【F:getconnects_admin/routes/notifications.py†L33-L40】
- `notification_detail(log_id)`: GET `/notifications/<id>` renders detail page for a single log entry. 【F:getconnects_admin/routes/notifications.py†L42-L49】

#### `routes/webhooks.py`
- Constants define writable field whitelists for campaigns and leads. 【F:getconnects_admin/routes/webhooks.py†L13-L28】
- `_extract(obj, path)`: Parses dotted/array notation paths (e.g., `foo[0].bar`) to extract nested values from JSON payloads. 【F:getconnects_admin/routes/webhooks.py†L30-L51】
- `justcall_webhook(token)`: POST `/webhooks/justcall/<token>` validates token, stores payload log, applies optional field mappings (with campaign lookup convenience), creates campaigns or leads via `create_lead`, and handles integrity errors gracefully. Returns 204 or conflict JSON on failure. 【F:getconnects_admin/routes/webhooks.py†L53-L166】
- `justcall_latest(token)`: GET `/webhooks/justcall/<token>/latest` returns most recent payload for inspection. 【F:getconnects_admin/routes/webhooks.py†L168-L181】
- `justcall_get_mapping(token)`: GET `/webhooks/justcall/<token>/mapping` returns stored mapping JSON. 【F:getconnects_admin/routes/webhooks.py†L183-L191】
- `justcall_save_mapping(token)`: POST `/webhooks/justcall/<token>/mapping` saves mapping JSON, handling integrity errors on commit. 【F:getconnects_admin/routes/webhooks.py†L193-L213】

## Test suite

The `tests/` package exercises application components. Each function below corresponds to a pytest test.

- `tests/conftest.py`
  - Fixtures configuring the Flask app, database session, and Supabase mocks used across tests. 【F:tests/conftest.py†L1-L120】

- `tests/test_app.py`
  - `test_client_crud`: Verifies client CRUD helpers and ORM integration. 【F:tests/test_app.py†L7-L28】
  - `test_lead_crud`: Ensures lead create/list/update/delete flows work with campaign linkage. 【F:tests/test_app.py†L30-L73】
  - `test_list_campaigns_includes_lead_type_groups`: Confirms campaign service includes lead type groups. 【F:tests/test_app.py†L75-L93】
  - `test_get_stats`: Exercises dashboard stats aggregation. 【F:tests/test_app.py†L95-L121】
  - `test_verify_supabase_token`: Uses monkeypatch to validate Supabase token verification. 【F:tests/test_app.py†L123-L139】
  - `test_dashboard_route`: Asserts dashboard route renders for logged-in session. 【F:tests/test_app.py†L141-L162】
  - `test_leads_page_allows_adding_lead`: Checks `/leads` page handles form submission. 【F:tests/test_app.py†L164-L204】
  - `test_leads_page_allows_csv_import`: Validates CSV import functionality. 【F:tests/test_app.py†L206-L285】

- `tests/test_authorization.py`
  - Tests for permission decorators ensuring staff and superuser checks behave correctly. 【F:tests/test_authorization.py†L1-L120】

- `tests/test_client_delete.py`
  - `test_delete_client_success`/`test_delete_client_not_found`: Cover client deletion service outcomes. 【F:tests/test_client_delete.py†L1-L55】

- `tests/test_cli.py`
  - Tests CLI command `create-superuser` for initial promotion and authorisation enforcement. 【F:tests/test_cli.py†L1-L126】

- `tests/test_database_url.py`
  - Validates database URL normalisation and error handling. 【F:tests/test_database_url.py†L1-L96】

- `tests/test_db_bootstrap.py`
  - Covers table rename logic and schema detection helpers. 【F:tests/test_db_bootstrap.py†L1-L140】

- `tests/test_email_service.py`
  - Exercises Gmail service success/failure paths and missing credentials scenarios. 【F:tests/test_email_service.py†L1-L138】

- `tests/test_forms.py`
  - Ensures WTForms definitions validate required fields and optional inputs. 【F:tests/test_forms.py†L1-L76】

- `tests/test_gmail_settings.py`
  - Validates Gmail settings route behaviour for saving/deleting credentials. 【F:tests/test_gmail_settings.py†L1-L120】

- `tests/test_justcall.py`
  - Covers JustCall credential encryption, webhook mapping, and sync behaviour. 【F:tests/test_justcall.py†L1-L220】

- `tests/test_lead_notifications.py`
  - Asserts lead creation triggers notifications with correct templates and logging. 【F:tests/test_lead_notifications.py†L1-L220】

- `tests/test_lead_stats.py`
  - Tests stats endpoints and lead report generation. 【F:tests/test_lead_stats.py†L1-L130】

- `tests/test_login.py`
  - Exercises login/reset routes and session authentication logic. 【F:tests/test_login.py†L1-L130】

- `tests/test_navigation.py`
  - Verifies navigation links render correctly for authenticated sessions. 【F:tests/test_navigation.py†L1-L90】

- `tests/test_notification_logs.py`
  - Validates notification log listing endpoints and templates. 【F:tests/test_notification_logs.py†L1-L120】

- `tests/test_permissions.py`
  - Confirms page permission enforcement and caching. 【F:tests/test_permissions.py†L1-L150】

- `tests/test_profile.py`
  - Checks profile update route authentication and persistence. 【F:tests/test_profile.py†L1-L80】

- `tests/test_settings.py`
  - Covers settings blueprint routes (JustCall, templates, notifications) end-to-end. 【F:tests/test_settings.py†L1-L260】

- `tests/test_sms_service.py`
  - Exercises SMS service credential lookup, successful send, and failure logging. 【F:tests/test_sms_service.py†L1-L150】

- `tests/test_supabase_pooler.py`
  - Ensures Supabase pooler requirement enforcement for DATABASE_URL options. 【F:tests/test_supabase_pooler.py†L1-L70】

- `tests/test_webhook.py`
  - Tests webhook mapping extraction, campaign creation, and lead handling including error responses. 【F:tests/test_webhook.py†L1-L240】

