# IT Helpdesk & Incident Management System

An MVP for recording, assigning, tracking, and resolving IT support incidents.
It demonstrates relational database design, REST APIs, validation, lifecycle
business rules, SLA calculation, persistence, and basic automated testing.

> **Implementation note:** Priority is calculated on the backend from `impact`
> and `urgency`, each of which can be `low`, `medium`, or `high`. Incident
> events persist creation, update, status-change, and comment actions, but do
> not yet record an actor or complete before/after snapshots.

## Project Overview

The application gives a helpdesk team one place to:

- Create, view, update, filter, and delete incidents.
- Record requesters, categories, impact, urgency, calculated priority, and
  optional assignees.
- Move incidents through controlled lifecycle states.
- Add and retrieve comments.
- Calculate and store an SLA deadline.
- Display `"Overdue"` or `"Not overdue"` status.
- Monitor incident counts through a Streamlit dashboard.

The backend is a FastAPI REST API. The Streamlit frontend consumes that API
over HTTP. SQLAlchemy maps the relational data to SQLite.

## Problem Statement

IT teams need consistent ownership and visibility for technical issues. Without
a central incident record, requests can be lost, assignments are unclear, and
service targets are difficult to measure.

This system stores each incident with its requester, category, priority,
assignee, lifecycle status, timestamps, comments, events, and SLA deadline.
Validation and service-layer rules prevent invalid references and lifecycle
transitions.

## Features

### Implemented

- User and category creation/listing.
- Incident CRUD operations.
- Incident filtering by status, priority, assignee, category, and requester.
- Incident comments.
- Persistent SQLite storage.
- Persistent incident events for creation, updates, status changes, and comments.
- Priority-based SLA deadlines:
  - Critical: 1 hour
  - High: 4 hours
  - Medium: 8 hours
  - Low: 24 hours
- Resolution-aware overdue calculation.
- Streamlit dashboard metrics and incident table.
- FastAPI Swagger documentation.
- Focused pytest coverage for SLA and API behavior.

### Not implemented

- Authentication or authorization.
- Impact/urgency priority calculation is implemented; a richer configurable
  matrix is not.
- `"At Risk"` SLA state.
- Pagination or full-text search.
- Notifications, attachments, or background jobs.
- Production deployment and formal database migrations.
- Optimistic locking for concurrent edits.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Application language. |
| FastAPI | Typed REST API, validation integration, dependency injection, and OpenAPI docs. |
| Streamlit | Python-based dashboard client. |
| SQLAlchemy | ORM models, relationships, sessions, queries, and transactions. |
| SQLite | Zero-configuration relational database for the MVP. |
| pytest | Automated unit-style and API tests. |
| Uvicorn | ASGI server for FastAPI. |
| Requests | HTTP client used by Streamlit. |

React, Node.js, Docker, Kubernetes, Redis, Kafka, and microservices were
intentionally avoided to keep the MVP focused and easy to run locally.

## Architecture

```text
+----------------------+
|     Streamlit UI     |
+----------------------+
           |
           | HTTP requests
           v
+----------------------+
|  FastAPI REST API    |
+----------------------+
           |
           v
+----------------------+
| Service / Business   |
| Logic                |
+----------------------+
           |
           v
+----------------------+
| SQLAlchemy ORM       |
+----------------------+
           |
           v
+----------------------+
| SQLite               |
+----------------------+
```

- **Streamlit:** Displays metrics, incidents, forms, and status controls.
- **FastAPI:** Exposes resource-oriented HTTP endpoints and response schemas.
- **Services:** Centralizes SLA, validation, and lifecycle rules.
- **SQLAlchemy:** Maps Python models to tables and manages request sessions.
- **SQLite:** Persists application data in `data/helpdesk.db`.

The UI never accesses SQLite directly. It sends requests to FastAPI; the API
validates the request, uses SQLAlchemy, commits changes, and returns JSON.

## Project Structure

```text
IT-Helpdesk-Incident-System/
|
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   └── routers/
│   │       ├── health.py
│   │       ├── incidents.py
│   │       └── users.py
│   └── tests/
│       ├── test_api.py
│       └── test_sla.py
├── frontend/
│   └── streamlit_app.py
├── data/
│   └── helpdesk.db
├── docs/
│   ├── dashboard.png
│   ├── create_incident.png
│   └── update_incident.png
├── requirements.txt
└── README.md
```

## Database Design

The database contains `users`, `categories`, `incidents`,
`incident_comments`, and `incident_events`.

```text
users 1 -------- N incidents N -------- 1 categories
  |                 |
  |                 +-------- N incident_comments
  |                 |
  |                 +-------- N incident_events
  |
  +------ requester and assignee relationships
```

### Users

`users` contains `id` (primary key), `name`, unique `email`, `role`, and
`created_at`. One user can request incidents, be assigned incidents, and author
comments.

### Categories

`categories` contains `id` (primary key) and unique `name`. One category can
classify many incidents.

### Incidents

`incidents` contains:

- `id` primary key
- `title`, `description`
- `status`, `impact`, `urgency`, and calculated `priority`
- `requester_id` foreign key to `users.id`
- nullable `assignee_id` foreign key to `users.id`
- `category_id` foreign key to `categories.id`
- `created_at`, `updated_at`
- nullable `resolved_at`, `closed_at`
- `sla_due_at`

Indexes exist on `status`, `priority`, and `created_at`.

### Incident comments

`incident_comments` contains `id`, `incident_id`, `author_id`, `content`, and
`created_at`. It represents the one-to-many relationship between incidents and
comments.

### Incident events

`incident_events` contains `id`, `incident_id`, `event_type`, `description`,
and `created_at`. Events are written in the same SQLAlchemy transaction as
incident creation, updates, status changes, and comment creation.

## Business Logic

### Priority and SLA

The client supplies validated `impact` and `urgency` values. The backend
calculates priority and does not trust a priority sent by the UI:

```text
Impact + Urgency -> Priority -> SLA duration -> SLA deadline
                                                   -> Overdue / Not overdue
```

The rule is:

```text
High + High       -> Critical
High impact OR high urgency -> High
Medium or Medium  -> Medium
Low + Low         -> Low
```

The exact nine combinations are covered by tests.

```text
sla_due_at = created_at + SLA duration
```

For example, a High incident created at 10:00 AM has a 4-hour SLA and a
deadline of 2:00 PM.

For active incidents:

```text
overdue = current_time > sla_due_at
```

For resolved incidents, the system compares `resolved_at` with `sla_due_at`,
so an incident resolved before its deadline remains `"Not overdue"` later.

### Lifecycle

```text
open -> in_progress -> resolved -> closed
```

- An incident starts as `open`.
- An assignee is required before `in_progress`.
- `resolved_at` is set when resolving.
- `closed_at` is set when closing.
- Reopening to `in_progress` clears `resolved_at`.
- Closed incidents cannot be modified.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check. |
| POST | `/users` | Create a user. |
| GET | `/users` | List users. |
| GET | `/users/{user_id}` | Retrieve a user. |
| POST | `/categories` | Create a category. |
| GET | `/categories` | List categories. |
| POST | `/incidents` | Create an incident and calculate its SLA. |
| GET | `/incidents` | List/filter incidents. |
| GET | `/incidents/{incident_id}` | Retrieve an incident. |
| PUT | `/incidents/{incident_id}` | Update incident fields. |
| PATCH | `/incidents/{incident_id}/status` | Apply a lifecycle transition. |
| DELETE | `/incidents/{incident_id}` | Delete an incident. |
| POST | `/incidents/{incident_id}/comments` | Add a comment. |
| GET | `/incidents/{incident_id}/comments` | List comments. |

FastAPI documentation is available at `http://127.0.0.1:8000/docs`.

## Validation and Error Handling

Pydantic validates required fields, string lengths, positive IDs, email shape,
roles, priorities, statuses, and non-empty comments. The service layer checks
that referenced records exist and that assignees are agents or admins.

Common responses include:

- `400` for invalid business operations.
- `404` for missing records.
- `409` for duplicate user emails or category names.
- `422` for invalid request data.
- `204` for successful incident deletion.

## Dashboard

![IT Helpdesk dashboard](docs/dashboard.png)

![Create incident form](docs/create_incident.png)

![Update incident form](docs/update_incident.png)

The dashboard loads users, categories, and incidents from the API each run. It
displays total, open, in-progress, resolved, and overdue counts, along with
priority, formatted SLA due time, and SLA status.

## Testing

Run:

```powershell
venv\Scripts\Activate.ps1
$env:PYTHONPATH = "backend"
python -m pytest backend\tests -q
```

The tests cover all four SLA durations, deadline arithmetic, overdue and
non-overdue incidents, resolution before the deadline, API health, incident
creation, event persistence, and invalid status transitions.

## Setup and Running

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the API:

```powershell
uvicorn backend.app.main:app --reload
```

In a second terminal, activate the environment and start the dashboard:

```powershell
streamlit run frontend\streamlit_app.py
```

The dashboard is normally available at `http://localhost:8501`.
The SQLite database is created at `data/helpdesk.db`. Existing records are
preserved across API and Streamlit restarts.

## Interview Preparation

Project-specific interview questions and technical preparation are available
in:

[Interview Preparation Guide](docs/INTERVIEW_PREP.md)

## Future Improvements

- A richer configurable impact/urgency priority matrix.
- Richer event audit metadata such as actor and before/after values.
- Authentication and role-based authorization.
- PostgreSQL, migrations, pagination, and production deployment.
- Optimistic locking for concurrent updates.
- Notifications, attachments, and background jobs.
