-- Clean Database Schema for Getconnects Admin
-- This schema replaces all Alembic migrations with a single, clean SQL file

-- Core Tables
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    uid VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    first_name VARCHAR,
    last_name VARCHAR,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);
CREATE INDEX IF NOT EXISTS ix_users_uid ON users(uid);

CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR NOT NULL,
    contact_name VARCHAR NOT NULL,
    contact_email VARCHAR NOT NULL,
    phone VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_clients_id ON clients(id);

CREATE TABLE IF NOT EXISTS campaigns (
    id VARCHAR PRIMARY KEY,
    campaign_name VARCHAR NOT NULL,
    status VARCHAR,
    client_id INTEGER REFERENCES clients(id)
);

CREATE INDEX IF NOT EXISTS ix_campaigns_id ON campaigns(id);

-- Lead Type Tables
CREATE TABLE IF NOT EXISTS lead_type_groups (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS lead_types (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    group_id VARCHAR REFERENCES lead_type_groups(id)
);

-- Notification Templates (needed before client_lead_type_settings)
CREATE TABLE IF NOT EXISTS notification_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    sms_template TEXT,
    email_subject VARCHAR,
    email_text TEXT,
    email_html TEXT,
    is_default BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS client_lead_type_settings (
    client_id INTEGER REFERENCES clients(id),
    lead_type_id VARCHAR REFERENCES lead_types(id),
    sms_enabled BOOLEAN DEFAULT FALSE,
    email_enabled BOOLEAN DEFAULT FALSE,
    sms_template TEXT,
    email_subject VARCHAR,
    email_html TEXT,
    template_id INTEGER REFERENCES notification_templates(id),
    PRIMARY KEY (client_id, lead_type_id)
);

CREATE TABLE IF NOT EXISTS campaign_lead_type_groups (
    campaign_id VARCHAR REFERENCES campaigns(id),
    lead_type_group_id VARCHAR REFERENCES lead_type_groups(id),
    PRIMARY KEY (campaign_id, lead_type_group_id)
);

CREATE TABLE IF NOT EXISTS campaign_lead_types (
    campaign_id VARCHAR REFERENCES campaigns(id),
    lead_type_id VARCHAR REFERENCES lead_types(id),
    lead_type_name VARCHAR,
    sms_enabled BOOLEAN,
    email_enabled BOOLEAN,
    PRIMARY KEY (campaign_id, lead_type_id)
);

-- Lead and Notification Tables
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    phone VARCHAR,
    address VARCHAR,
    email VARCHAR,
    company VARCHAR,
    secondary_phone VARCHAR,
    lead_type VARCHAR,
    caller_name VARCHAR,
    caller_number VARCHAR,
    notes VARCHAR,
    client_id INTEGER REFERENCES clients(id),
    campaign_id VARCHAR REFERENCES campaigns(id),
    number_id VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_leads_id ON leads(id);
CREATE INDEX IF NOT EXISTS ix_leads_client_id ON leads(client_id);
CREATE INDEX IF NOT EXISTS ix_leads_campaign_id ON leads(campaign_id);

CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id),
    lead_id INTEGER REFERENCES leads(id),
    channel VARCHAR,
    status VARCHAR,
    message VARCHAR
);

CREATE INDEX IF NOT EXISTS ix_notification_logs_id ON notification_logs(id);
CREATE INDEX IF NOT EXISTS ix_notification_logs_client_id ON notification_logs(client_id);
CREATE INDEX IF NOT EXISTS ix_notification_logs_lead_id ON notification_logs(lead_id);

-- Integration Tables
CREATE TABLE IF NOT EXISTS justcall_credentials (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR NOT NULL,
    api_secret VARCHAR NOT NULL,
    sms_number VARCHAR
);

CREATE TABLE IF NOT EXISTS justcall_webhooks (
    id SERIAL PRIMARY KEY,
    token VARCHAR NOT NULL UNIQUE,
    target_type VARCHAR NOT NULL,
    mapping JSONB
);

CREATE TABLE IF NOT EXISTS justcall_webhook_payloads (
    id SERIAL PRIMARY KEY,
    token_id INTEGER NOT NULL REFERENCES justcall_webhooks(id),
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_justcall_webhook_payloads_token_id ON justcall_webhook_payloads(token_id);

CREATE TABLE IF NOT EXISTS gmail_credentials (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    from_email VARCHAR,
    cc_emails VARCHAR,
    bcc_emails VARCHAR,
    api_client_id VARCHAR,
    api_client_secret VARCHAR,
    api_refresh_token VARCHAR,
    api_from_email VARCHAR
);

-- Permission Tables
CREATE TABLE IF NOT EXISTS page_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    path VARCHAR NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_page_permissions_user_id ON page_permissions(user_id);

-- Enable Row Level Security (RLS) for Supabase
-- Note: This is optional and can be configured separately in Supabase dashboard
-- Uncomment if you want to enable RLS for all tables

/*
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_type_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_lead_type_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_lead_type_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_lead_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE justcall_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE justcall_webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE justcall_webhook_payloads ENABLE ROW LEVEL SECURITY;
ALTER TABLE gmail_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE page_permissions ENABLE ROW LEVEL SECURITY;
*/

