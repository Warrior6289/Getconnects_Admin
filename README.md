# Getconnects Admin

Getconnects Admin is a minimal Flask application with a sleek interface. Animated gradient backgrounds, glass-morphism cards and subtle fade-in effects give the pages a modern feel. The app demonstrates how to log in, display a dashboard and manage clients stored in a SQL database (PostgreSQL or SQLite).

## Documentation

For a full tour of the architecture, data model, and operational procedures, see the [technical documentation](docs/TECHNICAL_OVERVIEW.md). Detailed, function-by-function explanations of the codebase live in the [code reference](docs/CODE_REFERENCE.md).

## Prerequisites

* Python 3.10+
* Optional: a running PostgreSQL instance and database (defaults to SQLite)

## Environment variables

Set the following variables before running the application:

```bash
export FLASK_CONFIG=development  # or production
export DATABASE_URL=postgresql://user:password@localhost:5432/dbname  # optional
export FLASK_SECRET_KEY=<your-secret-key>
export ENCRYPTION_KEY=<fernet-secret-key>
# Supabase configuration
export SUPABASE_URL=<your-supabase-url>
export SUPABASE_ANON_KEY=<your-anon-key>
export SUPABASE_SERVICE_KEY=<your-service-role-key>  # server-side only
```

With `python-dotenv` installed, values defined in a `.env` file are loaded automatically at startup.

`FLASK_SECRET_KEY` and `ENCRYPTION_KEY` have no defaults. When running with the production configuration the application exits if either is missing. Store `ENCRYPTION_KEY` and `SUPABASE_SERVICE_KEY` in a secure secrets manager and rotate them regularly to limit the impact of a potential leak.

`DATABASE_URL` points SQLAlchemy to your database. If you're using Supabase, copy the Postgres connection string from the project's settings and assign it to this variable. If unset, the app uses an in-memory SQLite database. The Supabase values are used by the login page to initialise the Supabase client SDK and allow the backend to verify tokens via functions in `services/auth_service`. The service role key should stay on the server and must never be exposed to browser clients.

## Getting started

1. Clone this repository and open it in VS Code.
2. Create a virtual environment and install requirements:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run database migrations (required as the app no longer creates tables automatically):

```bash
alembic upgrade head
```

4. Start the application:

```bash
python app.py
```

5. Open `http://localhost:5000` in your browser.

The interface uses a Bootstrap-based theme for a clean, professional look branded as the "GetConnects Portal". The pages feature animated gradient backgrounds, glass-card effects and fade-in animations for a polished appearance.

## Supabase authentication

1. Create a Supabase project and enable Email/Password authentication.
2. From the Supabase dashboard, copy the URL, anon key and service role key for your project. The service role key is for server-side use only and must never be exposed in client-side code or the browser.
3. Set the environment variables listed above with these values.
4. On startup, the app injects the URL and anon key into the login page so the Supabase client SDK can initialise.
5. After a user signs in, the frontend sends the Supabase JWT to `/sessionLogin`. The backend verifies it with the Supabase client and stores the user's UID in the Flask session cookie, establishing the session.

## File overview

* `app.py` – main Flask application. Handles authentication, dashboard and client management. Run `alembic upgrade head` before starting the app to ensure the database schema is up to date.
* `models/` – SQLAlchemy models and database session setup.
* `requirements.txt` – Python dependencies.
* `templates/` – HTML templates used by the app:
  * `login.html`
  * `dashboard.html`
  * `clients.html`

## How client creation works

* When you submit the *Add Client* form a record with the company name, contact details and phone number is inserted into the `clients` table.
* The clients page queries the configured database to list all existing clients including the creation time.
* Campaigns and leads are stored in related tables linked back to the client.

## ID generation

Each table uses an auto-incrementing integer primary key provided by the database engine.

## Customizing the app

* Set the `FLASK_SECRET_KEY` environment variable to a random value before using the app in production.
* Add additional pages or extend the SQLAlchemy models as needed.
* For deployment you could use services like Docker, Cloud Run or App Engine.

## Deployment

Ensure deployments run database migrations before starting the app (the application no longer creates tables automatically):

```bash
alembic upgrade head
```

This applies any outstanding migrations to the database schema.

## Running tests

The project includes a small test suite powered by `pytest`. Install it and run the tests from the repository root:

```bash
pip install pytest
pytest
```

## Database migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) for managing schema changes. Set `DATABASE_URL` to your database (e.g., PostgreSQL) and run:

```bash
alembic upgrade head
```

After updating the models, create a new migration with:

```bash
alembic revision --autogenerate -m "description"
```

## Creating a superuser

To bootstrap the first administrative account run the included CLI command. It
promotes a user to both `is_staff` and `is_superuser`:

```bash
FLASK_APP=app.py flask create-superuser alice@example.com --uid supabase-uid
```

Once a superuser exists, additional promotions must be authorised by an
existing superuser via the `--actor-email` option:

```bash
FLASK_APP=app.py flask create-superuser bob@example.com --uid bob-uid --actor-email alice@example.com
```

These commands can also be run with the `flask` executable on your PATH.

