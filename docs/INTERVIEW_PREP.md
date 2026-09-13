# IT Helpdesk & Incident Management System — Interview Preparation

This guide is based on the current implementation. It distinguishes implemented
behavior from proposed production improvements.

## 1. 60-Second Project Explanation

I built an IT Helpdesk and Incident Management System to centralize support
requests and track them from creation through closure. The frontend is a
Streamlit dashboard that communicates with a FastAPI REST API. FastAPI uses
Pydantic schemas for validation, a service layer for lifecycle and SLA rules,
and SQLAlchemy with SQLite for persistence. The database stores users,
categories, incidents, comments, and incident events. An incident has validated impact and urgency, a
backend-calculated priority, an optional assignee, lifecycle status,
timestamps, and a stored SLA deadline. Critical incidents have a one-hour SLA, High four hours,
Medium eight hours, and Low twenty-four hours. Active incidents are reported
as overdue when the current time passes the deadline; resolved incidents are
evaluated using their resolution time. I also wrote pytest tests for the SLA
rules and an API flow. Authentication and production concurrency controls are
future improvements, not current features.

## 2. 2-Minute Project Explanation

The business problem is that IT support requests need a consistent record of
ownership, category, priority, status, comments, and resolution target.
Without that, requests can be lost and service performance is difficult to
measure.

The application is a modular monolith. Streamlit is the client, FastAPI is
the REST boundary, service functions contain business rules, SQLAlchemy maps
models to SQLite, and request-scoped sessions commit changes. The dashboard
does not read the database directly; it calls the API and reloads incident
data from `GET /incidents`.

The relational database contains users, categories, incidents,
incident_comments, and incident_events. Incidents reference users as requester
and optional assignee, and reference a category. Comments and events are
separate one-to-many tables. The incident table stores status, priority,
timestamps, resolution and closure timestamps, and `sla_due_at`. Indexes are
declared on status, priority, and creation time.

The API supports user and category operations, incident CRUD, filters, status
transitions, comments, and a health check. Pydantic validates request bodies.
The service layer validates foreign-key references, requires an agent or admin
as assignee, enforces lifecycle transitions, calculates SLA deadlines, and
determines overdue status.

Priority is calculated on the backend from validated impact and urgency values.
High impact plus high urgency produces Critical. High impact or urgency
produces High; otherwise medium values produce Medium and low plus low
produces Low. SLA calculation adds one, four, eight, or
twenty-four hours to the creation time. A resolved incident is evaluated using
`resolved_at`, so resolving before the deadline remains successful even when
the record is viewed later.

The tests directly exercise SLA calculations and use FastAPI `TestClient` for
health, creation, event persistence, and invalid status transitions. For
production I would add authentication, authorization, PostgreSQL, migrations,
pagination, optimistic locking, notifications, and richer audit metadata.

## 3. Project Architecture

```text
+----------------------+
|     Streamlit UI     |
+----------------------+
           |
           | HTTP/JSON
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
| SQLite database      |
+----------------------+
```

### Request flow

1. A user submits a Streamlit form.
2. Streamlit sends JSON to a FastAPI endpoint using Requests.
3. FastAPI converts the body into a Pydantic schema.
4. The router calls validation and service functions.
5. SQLAlchemy uses a request-scoped session to query or write SQLite.
6. The route commits successful changes and returns a response model.
7. Streamlit reruns and requests current data from the API again.

### Responsibilities

- `frontend/streamlit_app.py`: client presentation and API calls.
- Routers: HTTP paths, dependency injection, and response handling.
- `schemas.py`: request/response contracts and field validation.
- `services.py`: SLA, reference, and lifecycle rules.
- `models.py`: relational entities and relationships.
- `database.py`: engine, session factory, table creation, and seed data.

## 4. Database & DBMS Questions

### What tables exist?

`users`, `categories`, `incidents`, `incident_comments`, and
`incident_events`.

### What is the primary key?

Each table has an integer `id` primary key. It uniquely identifies a row and
is used by foreign-key relationships.

### What foreign keys exist?

`incidents.requester_id` and `incidents.assignee_id` reference `users.id`.
`incidents.category_id` references `categories.id`.
`incident_comments.incident_id` references `incidents.id`.
`incident_comments.author_id` references `users.id`.
`incident_events.incident_id` references `incidents.id`.

### Why are relationships useful?

They represent real domain relationships without copying user, category, or
incident data into every related row. SQLAlchemy relationships also make
navigation and cascading comment/event cleanup explicit.

### How is the schema normalized?

Users and categories are stored once and referenced by IDs. Comments and events
are separate because an incident can have many of them. This avoids repeating
incident columns and reduces update anomalies.

### Which indexes exist?

The incident table declares indexes on `status`, `priority`, and `created_at`.
They match the common list filters and newest-first ordering. More indexes
should be added only after measuring query patterns.

### How do transactions work?

Routes add objects to a SQLAlchemy session and call `commit()`. For duplicate
user/category constraints, the code rolls back after `IntegrityError` and
returns a conflict. Incident and its event are committed in the same
transaction.

### How does persistence work?

The engine points to an absolute `data/helpdesk.db` path. Startup calls
`create_all`, which creates missing tables without dropping existing records.
The dashboard reloads from `GET /incidents`, so the SQLite database/API is the
source of truth rather than Streamlit state.

### Why SQLite?

SQLite is relational, local, zero-configuration, and sufficient for a
two-hour MVP. For production concurrency and operational scale, I would move
to PostgreSQL.

### Why not MongoDB?

The domain has strong relationships, foreign keys, status records, comments,
and events. A relational model makes those constraints and joins explicit.
MongoDB could work, but it is not necessary for this structured transactional
workflow.

## 5. SQL Interview Questions

The following examples describe the current schema. They are interview
examples; the application itself primarily uses SQLAlchemy ORM queries.

### SELECT

**Question:** List all incidents.

```sql
SELECT id, title, status, priority
FROM incidents;
```

**Answer:** `SELECT` chooses the columns and rows returned. This is equivalent
to the basic data needed for an incident list.

### WHERE

**Question:** Find open high-priority incidents.

```sql
SELECT id, title, sla_due_at
FROM incidents
WHERE status = 'open'
  AND priority = 'high';
```

**Answer:** `WHERE` filters rows before they are returned. This corresponds to
the API's status and priority filters.

### ORDER BY

**Question:** Show newest incidents first.

```sql
SELECT id, title, created_at
FROM incidents
ORDER BY created_at DESC;
```

**Answer:** Descending creation time matches the implemented incident list
ordering.

### GROUP BY

**Question:** Count incidents by status.

```sql
SELECT status, COUNT(*) AS incident_count
FROM incidents
GROUP BY status;
```

**Answer:** `GROUP BY` creates one aggregate group per status. This supports a
dashboard metric concept.

### HAVING

**Question:** Show categories with at least two incidents.

```sql
SELECT category_id, COUNT(*) AS incident_count
FROM incidents
GROUP BY category_id
HAVING COUNT(*) >= 2;
```

**Answer:** `HAVING` filters aggregate groups after grouping, unlike `WHERE`,
which filters individual rows.

### JOIN

**Question:** Show incident titles with requester and category names.

```sql
SELECT i.id, i.title, u.name AS requester, c.name AS category
FROM incidents AS i
JOIN users AS u ON u.id = i.requester_id
JOIN categories AS c ON c.id = i.category_id;
```

**Answer:** Joins combine normalized rows through foreign keys.

### LEFT JOIN

**Question:** Include unassigned incidents.

```sql
SELECT i.title, a.name AS assignee
FROM incidents AS i
LEFT JOIN users AS a ON a.id = i.assignee_id;
```

**Answer:** `LEFT JOIN` preserves incidents whose nullable assignee is `NULL`.

### Aggregate function

**Question:** Count overdue-looking records at the database level.

```sql
SELECT COUNT(*)
FROM incidents
WHERE status NOT IN ('resolved', 'closed')
  AND sla_due_at < CURRENT_TIMESTAMP;
```

**Answer:** This is a simplified SQL calculation. The application uses Python
datetime logic and uses `resolved_at` for resolved incidents.

### Subquery

**Question:** Find incidents whose category has more than five incidents.

```sql
SELECT id, title, category_id
FROM incidents
WHERE category_id IN (
    SELECT category_id
    FROM incidents
    GROUP BY category_id
    HAVING COUNT(*) > 5
);
```

**Answer:** The subquery identifies high-volume categories; the outer query
returns their incidents.

### Query optimization

For a large dataset, I would use `EXPLAIN QUERY PLAN`, verify indexes match
filters, paginate results, select only required columns, and avoid loading
all incidents into the dashboard.

## 6. FastAPI & REST Questions

### What is REST here?

The API exposes resources using URLs and standard HTTP methods. Incidents,
users, categories, and comments have resource endpoints and JSON
request/response bodies.

### GET vs POST vs PATCH

GET reads without intentionally changing state. POST creates a resource.
PATCH applies a focused partial change; this project uses it for status
transitions. PUT updates incident fields and DELETE removes an incident.

### Why separate status PATCH from field PUT?

Status changes have business side effects such as lifecycle validation and
timestamp updates. A separate endpoint makes that operation explicit.

### Which status codes are used?

`201` for created users, categories, incidents, and comments; `204` for
successful deletion; `400` for invalid operations; `404` for missing records;
`409` for duplicate unique values; and `422` for schema validation.

### How does validation work?

FastAPI parses request bodies into Pydantic models. Enums restrict roles,
priorities, and statuses. Field constraints restrict lengths and positive IDs.
The service layer performs database-aware validation after schema validation.

### How are API errors handled?

Expected domain failures raise `HTTPException`. Duplicate database constraints
are caught and rolled back in user/category creation. Unexpected errors are not
silently converted into successful responses.

### How does the client communicate?

Streamlit uses the Requests library to call the API. It handles HTTP errors
and displays a connection or request error in the dashboard.

## 7. Problem-Solving Questions

### Priority calculation

**Question:** How does Impact + Urgency produce Priority?

**Answer:** The backend calculates it. High impact plus high urgency produces
Critical. High impact or high urgency produces High. If neither is high, a
medium impact or urgency produces Medium; low plus low produces Low. The
Streamlit UI shows the calculated value but does not submit priority.

### SLA calculation

**Question:** How is the SLA calculated?

**Answer:** The service uses a dictionary:

```text
critical -> 1 hour
high     -> 4 hours
medium   -> 8 hours
low      -> 24 hours
```

It computes `created_at + duration` and stores the result in `sla_due_at`.

### What edge cases exist?

- Missing requester, category, or assignee.
- Assignee with requester role.
- Invalid enum values.
- Starting work without an assignee.
- Invalid status transitions.
- Editing a closed incident.
- Resolving before or after the SLA deadline.
- Changing priority and recalculating from original creation time.

### What is the overdue rule?

Active incidents compare current UTC time to `sla_due_at`. Resolved incidents
compare `resolved_at` to the deadline. Equal-to-deadline is not overdue because
the implemented comparison is strictly greater than.

## 8. Incident Lifecycle Questions

### Explain the lifecycle.

```text
open -> in_progress -> resolved -> closed
```

`in_progress` can return to `open`; `resolved` can return to
`in_progress`. Closed incidents have no allowed transitions.

### What happens in the database?

The status is updated and `updated_at` is refreshed. Resolving writes
`resolved_at`; closing writes `closed_at`; reopening to `in_progress` clears
`resolved_at`. A corresponding `IncidentEvent` is committed in the same
transaction.

### Why require an assignee?

It prevents work from entering `in_progress` without an owner. The service
checks that `assignee_id` is present before allowing that transition.

## 9. IncidentEvent / Audit Trail Questions

### Why does IncidentEvent exist?

An incident row stores current state. An event row stores a record of important
actions, allowing creation, update, status-change, and comment actions to remain
traceable without overwriting the incident's current values.

### What is the relationship?

One `Incident` has many `IncidentEvent` records through `incident_id`. Events
are deleted with their incident through the SQLAlchemy relationship cascade.

### Why a separate table?

Embedding an unbounded event list in an incident row would be difficult to query
and would overwrite history. A normalized child table supports many events and
time ordering.

### What is not captured?

The current event record does not capture actor identity, deletion events, or
complete old/new snapshots. Those are future audit improvements.

### How is traceability maintained?

The incident router creates an event for creation, updates, status changes, and
comments, then commits the event with the underlying action in one transaction.

## 10. Testing Questions

### What tests exist?

`test_sla.py` tests every priority duration, deadline arithmetic, overdue and
non-overdue cases, and resolved-before-SLA behavior.

`test_api.py` tests the health endpoint, incident creation, initial SLA
response, creation event persistence, and invalid direct closure from `open`.

### What is unit testing here?

The SLA tests call service functions directly with controlled datetimes. They
are fast and isolate business behavior from HTTP and UI concerns.

### What is API testing here?

The API tests use FastAPI `TestClient`, which exercises routing, startup table
initialization, database access, serialization, and HTTP status codes together.

### What manual test should be performed?

Start the API and dashboard, create an incident, refresh Streamlit, restart
the API, and verify that the incident remains visible. Inspect `data/helpdesk.db`
to verify both the incident and its creation event.

### What tests would you add?

I would add endpoint coverage for comments, deletion, duplicate conflicts,
missing IDs, all lifecycle transitions, closed updates, event contents, and
concurrent update behavior.

## 11. System Design Questions

### How would you scale this application?

Move from SQLite to PostgreSQL, add migrations, configure pooling, paginate
incident lists, run multiple stateless API instances, and put a load balancer
in front. These are proposed changes, not implemented features.

### What happens with 100,000+ incidents?

The current list endpoint returns all matching incidents, so pagination would
be necessary. I would add indexes based on query plans, select only required
columns, and precompute or cache expensive dashboard aggregates if needed.

### Why move to PostgreSQL?

PostgreSQL provides stronger production concurrency, operational tooling,
backups, scaling options, and richer indexing than a local SQLite file.

### Where would indexes be added?

The current code indexes incident status, priority, and creation time. In
production I would measure queries and consider indexes for foreign keys and
common composite filters such as `(status, priority, created_at)`.

### How handle concurrent updates?

The current model has no version column, so conflicting writes could use
last-write behavior. I would add optimistic locking with a version or
`updated_at` check and return `409 Conflict` for stale updates.

### How improve reliability?

Use PostgreSQL backups and migrations, health checks, structured logs,
monitoring, retries where safe, database constraints, automated tests, and
deployment checks. None is fully implemented in this MVP.

## 12. Security Questions

### What security is currently implemented?

Pydantic validates input, SQLAlchemy ORM queries avoid string-built SQL, and
database unique constraints protect duplicate emails and category names.
These are safeguards, not a complete security model.

### Is authentication implemented?

No. Users and roles exist, but roles are not authentication or authorization.

### How would you add authorization?

Add authenticated identities and enforce role/resource permissions in FastAPI
dependencies. For example, only authorized agents could update assigned work.

### How is SQL injection addressed?

The application uses SQLAlchemy ORM filters rather than concatenating request
strings into SQL. Any future raw SQL would need parameter binding and review.

### How protect secrets?

Use environment variables or a secrets manager for credentials and signing
keys. Do not commit `.env` or Streamlit secrets.

### Why HTTPS and rate limiting?

HTTPS protects incident data in transit. Rate limiting reduces abuse and
accidental overload. Neither is configured by the local MVP.

## 13. Follow-Up / Trap Questions

### Why SQLite?

It minimizes setup and still demonstrates relational design and transactions.
I would use PostgreSQL for multi-instance production writes.

### Why not MongoDB?

The domain has clear relationships and foreign keys, so a relational schema is
the simpler fit for this MVP.

### Why Streamlit instead of React?

The project goal was a Python-only stack and a fast operational UI. Streamlit
demonstrates client/API separation without introducing Node.js.

### Why FastAPI?

It provides typed validation, dependency injection, standard HTTP behavior, and
OpenAPI documentation with little code.

### Why SQLAlchemy?

It expresses the schema and relationships in Python, provides sessions and
transactions, and avoids coupling route code to raw SQL.

### Is priority calculated instead of manually selected?

Yes. The UI submits impact and urgency, and the backend calculates priority.
The API's calculation is the source of truth.

### Why store the SLA deadline?

It preserves the deadline used for the incident and makes API/dashboard
reporting simple. Recalculation on every read is unnecessary.

### What happens if the server restarts?

The database file remains on disk. Startup creates only missing tables and
seeds users/categories only when those tables are empty. Incidents and events
are loaded from SQLite through the API after restart.

### What if two users update the same incident?

There is no optimistic locking currently, so a later commit could overwrite an
earlier one. Production code should add a version check.

### What would you change for production?

Authentication, authorization, PostgreSQL, migrations, pagination, audit
metadata, optimistic locking, monitoring, HTTPS, backups, rate limiting, and
deployment automation.

### Is there an At Risk state?

No. The current API returns only `"Overdue"` or `"Not overdue"`.

### Is there a complete audit timeline?

There are persisted event records for important actions, but no actor identity,
deletion event, or full before/after snapshots.

## 14. Code Walkthrough

### `backend/app/main.py`

Creates the FastAPI app, registers the health, user/category, and incident
routers, and calls `init_db()` during startup.

### `backend/app/database.py`

- `DATABASE_PATH`: resolves the persistent SQLite file path.
- `engine`: SQLAlchemy SQLite engine with web-app thread configuration.
- `SessionLocal`: session factory.
- `Base`: declarative model base.
- `get_db()`: yields and closes a request-scoped session.
- `init_db()`: creates missing tables and calls seed logic.
- `seed_data()`: inserts sample users/categories only when their tables are
  empty.

### `backend/app/models.py`

- `User`: requester, agent, or admin data.
- `Category`: incident classification.
- `Incident`: current incident state, relationships, timestamps, and SLA.
- `IncidentComment`: many comments per incident.
- `IncidentEvent`: persisted action records.
- `utc_now()`: produces naive UTC datetimes for SQLite storage.

### `backend/app/schemas.py`

Defines `UserRole`, `Priority`, and `IncidentStatus` enums plus request and
response models such as `IncidentCreate`, `IncidentUpdate`, `StatusUpdate`,
`IncidentRead`, `CommentCreate`, and `CommentRead`.

### `backend/app/services.py`

- `SLA_HOURS`: actual priority-to-duration mapping.
- `calculate_sla_due_at()`: adds the SLA duration to creation time.
- `is_overdue()`: compares current/resolution time to the deadline.
- `sla_status()`: returns `"Overdue"` or `"Not overdue"`.
- `get_or_404()`: shared database lookup error.
- `validate_references()`: validates requester, category, assignee, and role.
- `change_status()`: enforces transitions and updates lifecycle timestamps.

### `backend/app/routers/incidents.py`

Implements incident CRUD, filtering, status transitions, comments, event
creation, response conversion, and transaction commits.

### `backend/app/routers/users.py`

Implements user and category creation/listing and user retrieval. It catches
unique-constraint errors for duplicate emails and category names.

### `backend/app/routers/health.py`

Implements `GET /health`.

### `frontend/streamlit_app.py`

Loads users, categories, and incidents with `api_request()`, formats SLA
timestamps with `format_sla_due()`, displays metrics/table data, and submits
create/status requests. It does not use session state as the persistence
source.

### Tests

`backend/tests/test_sla.py` isolates service logic. `backend/tests/test_api.py`
uses `TestClient` to exercise the HTTP/application path.

## 15. Interview Questions — Rapid Revision

**Q: What is the architecture?**  
A: Streamlit -> FastAPI -> services -> SQLAlchemy -> SQLite.

**Q: What is the source of truth?**  
A: SQLite, accessed through the API.

**Q: What does `create_all` do?**  
A: Creates missing tables; it does not reset existing records.

**Q: What are the SLA durations?**  
A: Critical 1h, High 4h, Medium 8h, Low 24h.

**Q: How is an active incident overdue?**  
A: `current_time > sla_due_at`.

**Q: How is a resolved incident evaluated?**  
A: `resolved_at > sla_due_at`.

**Q: What must happen before `in_progress`?**  
A: The incident must have an assignee.

**Q: What does a status change update?**  
A: Status, `updated_at`, relevant resolution/closure timestamp, and an event.

**Q: Is impact/urgency implemented?**  
A: Yes. Both are required on new incidents, and backend logic calculates the
priority for all nine combinations.

**Q: Is authentication implemented?**  
A: No; stored roles are not authorization.

**Q: Why separate events?**  
A: To preserve action records separately from current incident state.

**Q: How are duplicate users handled?**  
A: Database unique constraint, rollback, and HTTP 409.

**Q: What tests exist?**  
A: SLA unit-style tests and FastAPI API tests.

**Q: How would you scale it?**  
A: PostgreSQL, pagination, measured indexes, pooling, multiple API instances,
and a load balancer.

## 16. Key Things I Must Understand

- The exact Streamlit -> FastAPI -> SQLAlchemy -> SQLite request flow.
- The five current database tables and every foreign key.
- Why comments and events are separate one-to-many tables.
- How request-scoped SQLAlchemy sessions commit and close.
- Why `create_all` and conditional seeding preserve existing records.
- The exact priority enum and SLA duration mapping.
- The difference between active and resolved overdue calculations.
- Every allowed and rejected lifecycle transition.
- Why an assignee is required before `in_progress`.
- What `IncidentEvent` records and what it does not record.
- Which API methods and status codes are implemented.
- Which tests are automated and which scenarios are manual.
- Which security and scaling features are future improvements.
- The nine impact/urgency combinations and their calculated priorities.
