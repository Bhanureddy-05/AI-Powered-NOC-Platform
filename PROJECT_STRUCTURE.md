# Project Reorganization & System Architecture

This document details the clean, restructured directory tree, components, data flows, and internal architectures of the AI-Powered NOC Platform.

---

## Final Project Directory Tree

```
AI-Powered-NOC-Platform/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── routes/
│   │   │       │   ├── alerts.py
│   │   │       │   ├── audit.py
│   │   │       │   ├── auth.py
│   │   │       │   ├── copilot.py
│   │   │       │   ├── devices.py
│   │   │       │   ├── metrics.py
│   │   │       │   ├── ml.py
│   │   │       │   ├── reports.py
│   │   │       │   ├── tickets.py
│   │   │       │   └── ws.py
│   │   │       └── api.py
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   └── security.py
│   │   │   ├── db/
│   │   │   │   ├── base.py
│   │   │   │   ├── init_db.py
│   │   │   │   └── session.py
│   │   │   ├── models/
│   │   │   │   ├── alert.py
│   │   │   │   ├── alert_history.py
│   │   │   │   ├── audit_log.py
│   │   │   │   ├── copilot_message.py
│   │   │   │   ├── copilot_session.py
│   │   │   │   ├── device.py
│   │   │   │   ├── metric.py
│   │   │   │   ├── ticket.py
│   │   │   │   ├── ticket_comment.py
│   │   │   │   ├── ticket_history.py
│   │   │   │   └── user.py
│   │   │   ├── schemas/
│   │   │   │   ├── alert.py
│   │   │   │   ├── audit.py
│   │   │   │   ├── copilot.py
│   │   │   │   ├── device.py
│   │   │   │   ├── metric.py
│   │   │   │   ├── ml.py
│   │   │   │   ├── ticket.py
│   │   │   │   └── user.py
│   │   │   ├── services/
│   │   │   │   ├── alerts.py
│   │   │   │   ├── copilot.py
│   │   │   │   ├── reports.py
│   │   │   │   ├── tickets.py
│   │   │   │   └── ws.py
│   │   │   └── utils/
│   │   │       └── __init__.py
│   │   ├── data/
│   │   │   └── runbooks/
│   │   │       ├── auth_failure_runbook.md
│   │   │       ├── cpu_spike_runbook.md
│   │   │       └── latency_sla_runbook.md
│   │   ├── ml/
│   │   │   ├── anomaly_detection.py
│   │   │   ├── failure_prediction.py
│   │   │   ├── predict.py
│   │   │   ├── train.py
│   │   │   └── saved_models/
│   │   ├── scripts/
│   │   │   ├── metric_generator.py
│   │   │   ├── reset_db.py
│   │   │   ├── seed_db.py
│   │   │   ├── verify_backend.py
│   │   │   ├── verify_copilot.py
│   │   │   ├── verify_devices.py
│   │   │   ├── verify_features.py
│   │   │   ├── verify_live.py
│   │   │   └── verify_metrics.py
│   │   ├── tests/
│   │   │   ├── test_copilot.py
│   │   │   ├── test_imports.py
│   │   │   └── test_rag.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── noc_platform.db
│   │   └── main.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── Toast.jsx
│   │   ├── context/
│   │   │   ├── AuthContext.jsx
│   │   │   └── WebSocketContext.jsx
│   │   ├── hooks/
│   │   ├── pages/
│   │   │   ├── Alerts.jsx
│   │   │   ├── Analytics.jsx
│   │   │   ├── AuditLogs.jsx
│   │   │   ├── Copilot.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Devices.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Reports.jsx
│   │   │   └── Tickets.jsx
│   │   ├── services/
│   │   │   ├── alerts.js
│   │   │   ├── api.js
│   │   │   ├── audit.js
│   │   │   ├── auth.js
│   │   │   ├── copilot.js
│   │   │   ├── devices.js
│   │   │   ├── metrics.js
│   │   │   ├── ml.js
│   │   │   ├── reports.js
│   │   │   └── tickets.js
│   │   ├── styles/
│   │   │   ├── App.css
│   │   │   └── index.css
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── PROJECT_STRUCTURE.md
└── .gitignore
```

---

## Backend Architecture

The backend application is designed using a **modular layered architecture** structured to separate presentation, validation, business orchestration, database storage, and offline analytical routines.

```
┌────────────────────────────────────────────────────────┐
│                   HTTP Clients (Web / scripts)         │
└──────────────────────────┬─────────────────────────────┘
                           │ Async Requests
                           ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Routing Shell (main.py)            │
│  - Middleware: CORS, Custome Rate Limiter              │
│  - Exception Handlers: Global Exceptions, SQL Error    │
└──────────────────────────┬─────────────────────────────┘
                           │ Injected Sessions
                           ▼
┌────────────────────────────────────────────────────────┐
│               API Endpoints (v1/routes/)                │
│  - Parameter Validations via Pydantic Schemas          │
│  - Auth & RBAC Guards: Depends(check_role)             │
└──────────────────────────┬─────────────────────────────┘
                           │ Calls Orchestrator
                           ▼
┌────────────────────────────────────────────────────────┐
│         Business Service Logic (app/services/)         │
│  - Database Transaction Context (async_session)        │
│  - Integration: AI Copilot, Report compilation         │
└──────────────────────────┬─────────────────────────────┘
                           │ ORM Queries
                           ▼
┌────────────────────────────────────────────────────────┐
│        Data Model Layer (app/models/ & app/db/)        │
│  - SQLAlchemy async engines & SQLite / PostgreSQL Base │
└────────────────────────────────────────────────────────┘
```

* **Core FastAPI Layer**: Handles the HTTP interface, JSON payload parsing, and standard SSE streams. A custom asynchronous rate-limiting middleware operates locally to limit login/registration requests to `30 req/min`.
* **RBAC & Authorization**: Decoded JWT tokens map roles (`admin`, `operator`, `viewer`) in route arguments via FastAPI `Depends()`, raising `403 Forbidden` if scope criteria fail.
* **Asynchronous Service Context**: Standardizes transaction boundaries. The controllers trigger DB operations asynchronously and generate log entries in the audit trail.
* **Background Daemons**: Mounts long-running background tasks on startup (e.g., ticket SLA check loops running every 60s and ML model retrain loops running every 24h).

---

## Frontend Architecture

The frontend is a dynamic client-side application built with **React**, **Vite**, **TailwindCSS**, and **Chart.js** leveraging global context providers and a clean API wrapper.

* **Routing and Guarding**: Uses `react-router-dom` to structure page paths. Router branches are nested within `ProtectedRoute` to block unauthenticated requests.
* **Context Providers**:
  - `AuthContext`: Tracks JWT token storage, user roles, token expirations, and triggers redirection to `/login` when token validity lapses.
  - `WebSocketContext`: Establishes a persistent socket stream on user login, capturing and routing server-sent alerts to the active screen automatically.
* **Service Module Layer**: Every service file (e.g. `services/devices.js`, `services/copilot.js`) abstracts away backend fetch calls, using a pre-configured HTTP client (`api.js`) which injects authorization headers.

---

## Database Models

The relational database schema is structured as follows:

```
                  ┌──────────────┐
                  │     User     │
                  └──────────────┘
                         │
                         ▼
┌──────────────┐  1:N ┌──────────────┐ 1:N ┌──────────────┐
│    Device    │─────►│    Alert     │─────►│ AlertHistory │
└──────────────┘      └──────────────┘     └──────────────┘
       │ 1:N                 │ 1:1
       ▼                     ▼
┌──────────────┐      ┌──────────────┐ 1:N ┌──────────────┐
│ DeviceMetric │      │    Ticket    │─────►│ TicketHistory│
└──────────────┘      └──────────────┘     └──────────────┘
                             │ 1:N
                             ▼
                      ┌──────────────┐
                      │ TicketComment│
                      └──────────────┘
```

* **`User`**: Tracks credentials, passwords (stored as bcrypt hashes), and roles (`admin`, `operator`, `viewer`).
* **`Device`**: Represents network nodes. Stores uniqueness parameters (unique device names and IP addresses) and tracks statuses (`active`, `maintenance`, `inactive`).
* **`DeviceMetric`**: Telemetry history. Stores CPU, memory, bandwidth, latency, and packet loss logs along with ML anomaly scores.
* **`Alert`**: Stores open/acknowledged/resolved triggers. Links `device_id` and tracks severe events (`critical`, `high`, `medium`, `low`).
* **`Ticket`**: Represents operations incidents. Contains a title, description, priorities, status trackers, and SLA deadlines.
* **`CopilotSession` & `CopilotMessage`**: Persists copilot message history.

---

## ML Pipeline

The platform runs two distinct machine learning pipelines using `scikit-learn` models:

```
[TELEMETRY INGESTION] ────► [Isolation Forest] ────► [Predict Anomaly Score]
                                  │
[HISTORICAL METRICS]  ────► [Random Forest]    ────► [Predict Time-to-Failure]
```

1. **Unsupervised Anomaly Detection (Isolation Forest)**:
   - Evaluates incoming metrics (`cpu_usage`, `memory_usage`, `latency`, `packet_loss`).
   - Fits model boundaries to normal telemetry configurations and scores new packets. Values above `0.7` indicate a significant anomaly, which raises alert warnings.
2. **Supervised Failure Prediction (Random Forest)**:
   - Classifies device health status.
   - Evaluates historical trends to output a calculated health score percentage and categorize overall device risk.
3. **Training Cycle**:
   - Persisted model binary files are saved in `ml/saved_models/`.
   - On startup, if binaries are missing, the server performs an initial training bootstrap.
   - An active daily daemon triggers model retraining from backend data, adapting parameters as new metrics accumulate.

---

## AI Copilot & RAG Flow

The AI Copilot uses a semantic search fallback loop to process network events:

```
[User Query] ────────► [Semantic Search] ────────► [Matching Runbooks (RAG)]
                             │
                             ▼
[Database Metrics] ──► [Structured Synthesis] ────► [Streaming SSE Report]
```

1. **RAG Indexing**:
   - During startup, `ResilientVectorStore` parses raw Markdown runbooks in `data/runbooks/` (`cpu_spike_runbook.md`, `latency_sla_runbook.md`, etc.).
   - If no LLM API credentials are configured, it initializes a local TF-IDF semantic vectorizer from the documents.
2. **Query Processing**:
   - When a user asks a troubleshooting question, the agent executes a cosine similarity search against the RAG vector store to identify the most relevant runbook.
   - The agent concurrently fetches live telemetries and critical alerts from the database.
3. **Synthesis and Streaming**:
   - Structured responses are generated using the template (Risk Level, Live Telemetry, Root Cause, Immediate Actions, Verification Commands, and References).
   - The result is streamed token-by-token using SSE (Server-Sent Events) to the frontend client.

---

## API Request Lifecycle

The following steps trace a network request through the AETHER platform:

```
[React View] ──► [HTTP Service Client] ──► [FastAPI Middleware] ──► [FastAPI Route Depends]
                                                                          │
[JSON Output] ◄── [Response Schema] ◄── [Service Layer] ◄── [SQL Database ORM] ◄┘
```

1. **Dispatch**: A user action triggers an API request via the frontend client (e.g. `services/devices.js`).
2. **Middleware Processing**: The backend rate-limiter verifies request frequencies, and CORS headers are injected.
3. **Authentication & Scope Validation**: FastAPI checks the `Authorization` header, extracts the bearer token, validates the signature, and confirms the client's role requirements.
4. **Validation**: The JSON payload is validated against a Pydantic schema (e.g. `DeviceCreate`). If schema constraints are violated (e.g. a negative latency value), it rejects the request with a `422 Unprocessable Entity` error.
5. **Business Logic Orchestration**: The controller queries or updates the database.
6. **Persistence & Auditing**: SQLAlchemy commits changes, triggers audit logging (e.g., `device_created`), and broadcasts update signals to active frontend users via WebSockets.
7. **Serialization & Response**: The return values are serialized through Pydantic schemas (excluding internal database variables), and returned as a JSON payload to the user.
