# Security Architecture

## Authentication Boundary

User authentication is owned by the App Platform.

Supabase/RLS authorization is owned by the App Platform.

The Financial Service MUST NOT:
- query Supabase directly
- contain Supabase credentials
- receive a user JWT for database access
- implement farm ownership rules

## Service Authentication

App Platform → Financial Service uses service-to-service
authentication.

The Financial Service trusts the authenticated service,
not the user's Supabase session.

## Data Minimization

The App Platform should send only the financial data required
for the requested calculation.

The Financial Service should not receive unrelated farm,
user, CRM, or conversation data.