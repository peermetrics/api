# API Server

> [!Note]
> This repo is only one part of the bigger peer metrics WebRTC monitoring service. Check out the full project [here](https://github.com/peermetrics/peermetrics).

This folder contains code for the API server used to ingest the metrics sent by the [SDK](https://github.com/peermetrics/sdk-js).

* [How it works](#how-it-works)
* [How to run locally](#how-to-run-locally)
  * [Prerequisites](#prerequisites)
  * [Environment Variables](#environment-variables)
  * [Database Setup](#database-setup)
  * [Running with Docker](#running-with-docker)
  * [Running Locally](#running-locally)
  * [Accessing Django Admin](#accessing-django-admin)
* [Authentication](#authentication)
  * [API Key Authentication](#api-key-authentication)
  * [JWT Token Flow](#jwt-token-flow)
  * [Public vs Private Endpoints](#public-vs-private-endpoints)
* [API Usage](#api-usage)
  * [Typical Workflow](#typical-workflow)
  * [SDK Integration](#sdk-integration)
  * [Web Interface Integration](#web-interface-integration)
* [Error Handling](#error-handling)
  * [Error Response Format](#error-response-format)
  * [HTTP Status Codes](#http-status-codes)
  * [Common Errors](#common-errors)
* [Tech Stack](#tech-stack)
  * [Models](#models)
    * [Organization](#organization)
    * [App](#app)
    * [Conference](#conference)
    * [Participant](#participant)
    * [Session](#session)
    * [Connection](#connection)
    * [Track](#track)
    * [GenericEvent](#genericevent)
  * [Model Relationships](#model-relationships)
  * [Routes](#routes)
    * [Public](#public)
    * [Private](#private)
* [Data Flow](#data-flow)
  * [Metric Ingestion](#metric-ingestion)
  * [Data Storage](#data-storage)
  * [Data Querying](#data-querying)

## How it works

This is a public API endpoint that has two functions:

- ingesting data collected by the SDK
- used for data query by `web`

In addition to this, the api has the django admin interface to check the raw data collected.

## How to run locally

### Prerequisites

Before running the API server locally, ensure you have the following installed:

- **Python 3.8** - The application is built with Python 3.8
- **Docker & Docker Compose** - For containerized deployment (recommended)
- **PostgreSQL** - Database for storing metrics (if running without Docker)
- **Redis** - For caching (optional but recommended)

### Environment Variables

The application uses environment variables for configuration. Copy the `.env` file and configure the following key variables:

```bash
# Django settings
DEBUG=True
DJANGO_SETTINGS_MODULE=api.settings
SECRET_KEY=your-secret-key-here

# JWT token secrets - used for authentication
INIT_TOKEN_SECRET=your-init-token-secret
SESSION_TOKEN_SECRET=your-session-token-secret

# Web domain for CORS
WEB_DOMAIN=localhost:8080

# Redis configuration (optional)
REDIS_HOST=redis://127.0.0.1:6379

# Database configuration
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_USER=peeruser
DATABASE_PASSWORD=peeruser
DATABASE_NAME=peerdb
CONN_MAX_AGE=14400

# Optional: Post-conference cleanup
POST_CONFERENCE_CLEANUP=False
```

**Key Environment Variables Explained:**

- `INIT_TOKEN_SECRET`: Secret used to sign JWT tokens returned by the `/initialize` endpoint
- `SESSION_TOKEN_SECRET`: Secret used to sign JWT tokens returned by the `/sessions` endpoint
- `WEB_DOMAIN`: Domain for CORS configuration, allows the web interface to query the API
- `DATABASE_*`: PostgreSQL connection parameters
- `REDIS_HOST`: Redis server location for caching (improves performance)
- `POST_CONFERENCE_CLEANUP`: If `True`, deletes unnecessary stats events after a conference ends

### Database Setup

The application uses PostgreSQL as its database. The database schema is managed through Django migrations.

**With Docker:**
The database is automatically created and migrations are applied when using Docker Compose.

**Without Docker:**

1. Create a PostgreSQL database:
```bash
createdb peerdb
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Create a superuser for Django admin access:
```bash
python manage.py createsuperuser
```

### Running with Docker

The recommended way to run the API server locally is using Docker:

1. Build and start the containers:
```bash
docker-compose up --build
```

2. The API server will be available at `http://localhost:8000`

3. To run in detached mode:
```bash
docker-compose up -d
```

4. To stop the containers:
```bash
docker-compose down
```

### Running Locally

To run the API server without Docker:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure PostgreSQL is running and configured in your `.env` file

3. Run migrations:
```bash
python manage.py migrate
```

4. Start the development server:
```bash
python manage.py runserver
```

5. The API server will be available at `http://localhost:8000`

For production deployments, use a WSGI server like Gunicorn:
```bash
gunicorn api.wsgi:application --bind 0.0.0.0:8000
```

### Accessing Django Admin

The Django admin interface allows you to view and manage the raw data collected by the API.

1. Create a superuser account (if not already done):
```bash
python manage.py createsuperuser
```

2. Access the admin interface at `http://localhost:8000/admin`

3. Log in with your superuser credentials

The admin interface provides access to all models including Organizations, Apps, Conferences, Sessions, Participants, Connections, and Events.

## Authentication

The API uses a two-tier JWT token authentication system to secure endpoints. The authentication flow differs between SDK (public) endpoints and web interface (private) endpoints.

### API Key Authentication

Each App has a unique API key used for initial authentication. The API key:
- Is a 32-character alphanumeric string
- Must be included in the first request to `/initialize`
- Is validated against the App model in the database
- Can be regenerated through the web interface if compromised

**Example API Key:**
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### JWT Token Flow

The authentication process involves two types of JWT tokens:

**1. Initialize Token (from `/initialize` endpoint)**

When the SDK first connects, it calls `/initialize` with an API key:

```json
POST /initialize
{
  "apiKey": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "conferenceId": "room-123",
  "userId": "user-456"
}
```

Response includes an initialize token:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "getStatsInterval": 10000,
  "batchConnectionEvents": false,
  "time": 1234567890.123
}
```

The initialize token payload contains:
```json
{
  "p": "participant-uuid",
  "c": "conference-uuid",
  "t": 1234567890.123
}
```

Token lifespan: 24 hours (configurable via `INIT_TOKEN_LIFESPAN`)

**2. Session Token (from `/sessions` endpoint)**

The initialize token is then used to create a session:

```json
POST /sessions
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "appVersion": "1.0.0",
  "platform": {...},
  "devices": {...}
}
```

Response includes a session token:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

The session token payload contains:
```json
{
  "s": "session-uuid",
  "t": 1234567890.123
}
```

Token lifespan: 24 hours (configurable via `SESSION_TOKEN_LIFESPAN`)

**3. Authenticated Requests**

All subsequent requests use the session token:

```json
POST /stats
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "connectionId": "connection-uuid",
  "data": {...}
}
```

### Public vs Private Endpoints

**Public Endpoints** (used by SDK):
- Do not require user authentication
- Use JWT tokens for authorization
- Rate-limited to prevent abuse
- Accept requests from any origin (with optional domain restrictions per App)

**Private Endpoints** (used by web interface):
- Require user authentication (session-based)
- Used for querying and managing data
- CORS-enabled for configured web domains
- Support filtering and pagination

## API Usage

### Typical Workflow

The standard flow for SDK integration follows these steps:

1. **Initialize**: SDK calls `/initialize` with API key → receives init token
2. **Create Session**: SDK calls `POST /sessions` with init token → receives session token
3. **Send Events**: SDK sends events (getUserMedia, connections, stats) with session token
4. **Query Data**: Web interface queries data using private endpoints

### SDK Integration

**Step 1: Initialize Connection**

```javascript
// SDK initialization
const response = await fetch('http://localhost:8000/initialize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    apiKey: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6',
    conferenceId: 'room-123',
    conferenceName: 'Team Meeting',
    userId: 'user-456',
    userName: 'John Doe'
  })
});

const { token: initToken, getStatsInterval } = await response.json();
```

**Step 2: Create Session**

```javascript
const sessionResponse = await fetch('http://localhost:8000/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    token: initToken,
    appVersion: '1.0.0',
    webrtcSdk: 'native',
    platform: {
      name: 'Chrome',
      version: '96.0.4664.110',
      os: 'Windows'
    },
    devices: {
      audio: { deviceId: 'default' },
      video: { deviceId: 'camera-1' }
    }
  })
});

const { token: sessionToken } = await sessionResponse.json();
```

**Step 3: Send Stats**

```javascript
// Send WebRTC stats periodically
setInterval(async () => {
  await fetch('http://localhost:8000/stats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token: sessionToken,
      connectionId: 'connection-uuid',
      data: {
        connection: {
          local: { candidateType: 'host' },
          remote: { candidateType: 'srflx' }
        },
        audio: {
          inbound: [...],
          outbound: [...]
        },
        video: {
          inbound: [...],
          outbound: [...]
        }
      }
    })
  });
}, getStatsInterval);
```

**Step 4: Send Connection Events**

```javascript
// When a peer connection is created
await fetch('http://localhost:8000/connection', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    token: sessionToken,
    type: 'addConnection',
    peerId: 'peer-uuid',
    peerName: 'Jane Doe',
    connectionState: 'connecting'
  })
});
```

### Web Interface Integration

**Query Sessions for a Conference**

```javascript
GET /sessions?conferenceId=conference-uuid

Response:
{
  "data": [
    {
      "id": "session-uuid",
      "participant": "participant-uuid",
      "conference": "conference-uuid",
      "created_at": "2024-01-15T10:30:00Z",
      "end_time": "2024-01-15T11:00:00Z",
      "duration": 1800,
      "platform": {...},
      "devices": {...}
    }
  ]
}
```

**Query Conference Details**

```javascript
GET /conferences/conference-uuid

Response:
{
  "data": {
    "id": "conference-uuid",
    "conference_id": "room-123",
    "conference_name": "Team Meeting",
    "start_time": "2024-01-15T10:30:00Z",
    "end_time": "2024-01-15T11:00:00Z",
    "duration": 1800,
    "ongoing": false,
    "app": "app-uuid"
  }
}
```

**Query Conference Events**

```javascript
GET /conferences/conference-uuid/events?type=stats

Response:
{
  "data": [
    {
      "id": "event-uuid",
      "type": "stats",
      "category": "S",
      "data": {...},
      "created_at": "2024-01-15T10:30:15Z",
      "participant": "participant-uuid",
      "session": "session-uuid"
    }
  ]
}
```

## Error Handling

### Error Response Format

All errors follow a consistent JSON format:

```json
{
  "error_code": "missing_parameters",
  "message": "Some parameters are missing from the request."
}
```

### HTTP Status Codes

The API uses standard HTTP status codes:

- `200 OK` - Request succeeded
- `400 Bad Request` - Invalid parameters or malformed request
- `401 Unauthorized` - Missing, invalid, or expired token
- `403 Forbidden` - Domain not allowed or insufficient permissions
- `404 Not Found` - Resource does not exist
- `405 Method Not Allowed` - HTTP method not supported for endpoint
- `500 Internal Server Error` - Server-side error

### Common Errors

**Authentication Errors:**

```json
// Missing token
{
  "error_code": "missing_token",
  "message": "No token supplied."
}

// Invalid token
{
  "error_code": "invalid_token",
  "message": "Invalid token."
}

// Expired token
{
  "error_code": "expired_token",
  "message": "Expired token."
}

// Invalid API key
{
  "error_code": "invalid_api_key",
  "message": "Invalid api key."
}
```

**Validation Errors:**

```json
// Missing parameters
{
  "error_code": "missing_parameters",
  "message": "Some parameters are missing from the request."
}

// Invalid parameters
{
  "error_code": "invalid_parameters",
  "message": "Some supplied parameters are not valid."
}

// Domain not allowed
{
  "error_code": "domain_not_allowed",
  "message": "The app does not allow this domain."
}
```

**Resource Errors:**

```json
// Conference not found
{
  "error_code": "conference_not_found",
  "message": "The requested conference does not exist."
}

// Participant not found
{
  "error_code": "participant_not_found",
  "message": "The requested participant does not exist."
}

// Connection not found
{
  "error_code": "connection_not_found",
  "message": "The requested connection does not exist."
}

// Connection ended
{
  "error_code": "connection_ended",
  "message": "This connection has ended and we are no longer listening for events."
}
```

**Application State Errors:**

```json
// App not recording
{
  "error_code": "app_not_recording",
  "message": "The requested app is not recording."
}

// Quota exceeded
{
  "error_code": "quota_exceeded",
  "message": "Quota exceeded."
}
```

## Tech Stack

- Language: Python 3.8
- Framework: Django
- DB: Postgres
- Cache: Redis (optional)

### Models

The main models from this project are:

#### Organization

An organization is a way to group apps and manage access control.

**Fields:**
- `id` (UUID): Unique identifier
- `name` (string): Organization name set by the owner
- `created_at` (datetime): When the organization was created
- `is_active` (boolean): Whether the organization is active

**Relationships:**
- Has many `Apps` (one-to-many)

#### App

An abstraction of an application being monitored by PeerMetrics.

**Fields:**
- `id` (UUID): Unique identifier
- `name` (string): App name set by user
- `api_key` (string): 32-character alphanumeric key used for SDK authentication
- `domain` (string, optional): Domain restriction for CORS (recommended for security)
- `organization` (FK): The organization that owns this app
- `interval` (integer): How often to collect stats in milliseconds (default: 10000)
- `recording` (boolean): Whether the app is actively recording metrics
- `durations_days` (JSON): Cache of call durations for billing period
- `created_at` (datetime): When the app was created

**Relationships:**
- Belongs to one `Organization` (many-to-one)
- Has many `Conferences` (one-to-many)
- Has many `Participants` (one-to-many)
- Has many `Events` (one-to-many)

#### Conference

A conference represents a WebRTC call where one or more participants are present. It gets created when a participant connects for the first time.

**Fields:**
- `id` (UUID): Unique identifier
- `conference_id` (string): Conference ID set by user (max 64 chars)
- `conference_name` (string, optional): Human-readable conference name
- `conference_info` (JSON): Additional conference metadata
- `start_time` (datetime): When the first participant connected
- `call_start` (datetime): When the current active call started
- `end_time` (datetime): When the last connection closed
- `ongoing` (boolean): Whether the call is currently active
- `duration` (integer): Total duration of active connections in seconds
- `app` (FK): The app that created this conference

**Relationships:**
- Belongs to one `App` (many-to-one)
- Has many `Participants` (many-to-many)
- Has many `Sessions` (one-to-many)
- Has many `Connections` (one-to-many)
- Has many `Events` (one-to-many)

#### Participant

A participant is an endpoint (e.g., browser) for which metrics are gathered. A participant is made unique by the combination of `app_id:participant_id`.

**Fields:**
- `id` (UUID): Unique identifier
- `participant_id` (string): Participant ID set by user (max 64 chars)
- `participant_name` (string, optional): Human-readable participant name
- `is_sfu` (boolean): Whether this participant is an SFU server
- `app` (FK): The app that created this participant
- `created_at` (datetime): When the participant was first seen

**Relationships:**
- Belongs to one `App` (many-to-one)
- Participates in many `Conferences` (many-to-many)
- Has many `Sessions` (one-to-many)
- Has many `Connections` (one-to-many)
- Has many `Events` (one-to-many)

#### Session

A session represents a participant's presence in a conference. A participant can have multiple sessions if they rejoin.

**Fields:**
- `id` (UUID): Unique identifier
- `conference` (FK): The conference this session belongs to
- `participant` (FK): The participant this session belongs to
- `constraints` (JSON): Media constraints used (audio/video settings)
- `devices` (JSON): Device information (camera, microphone)
- `platform` (JSON): Browser/OS information
- `metadata` (JSON): Custom metadata (max 5 keys)
- `geo_ip` (JSON): Geographic location data
- `app_version` (string): User's app version
- `webrtc_sdk` (string): WebRTC SDK being used
- `session_info` (JSON): Session-specific information and warnings
- `duration` (integer): Total session duration in seconds
- `created_at` (datetime): When the session started (start_time)
- `end_time` (datetime): When the session ended
- `call_start` (datetime): When the user had an active connection

**Relationships:**
- Belongs to one `Conference` (many-to-one)
- Belongs to one `Participant` (many-to-one)
- Has many `Connections` (one-to-many)
- Has many `Tracks` (one-to-many)
- Has many `Events` (one-to-many)
- Has many `Issues` (one-to-many)

#### Connection

A connection represents a WebRTC peer connection between two participants.

**Fields:**
- `id` (UUID): Unique identifier
- `session` (FK): The session this connection belongs to
- `conference` (FK): The conference this connection belongs to
- `participant` (FK): The local participant
- `peer` (FK): The remote participant
- `type` (string): Connection type (host, srflx, prflx, relay)
- `state` (string): Connection state (new, connecting, connected, disconnected, failed, closed)
- `connection_info` (JSON): Connection metadata including negotiations
- `start_time` (datetime): When the connection was created
- `end_time` (datetime): When the connection closed
- `duration` (integer): Connection duration in seconds

**Relationships:**
- Belongs to one `Session` (many-to-one)
- Belongs to one `Conference` (many-to-one)
- Belongs to one `Participant` as local (many-to-one)
- Belongs to one `Participant` as peer (many-to-one)
- Has many `Tracks` (one-to-many)
- Has many `Events` (one-to-many)
- Has many `Issues` (one-to-many)

#### Track

A track represents a media stream (audio or video) in a connection.

**Fields:**
- `id` (UUID): Unique identifier
- `session` (FK): The session this track belongs to
- `connection` (FK): The connection this track belongs to
- `track_id` (string): Track identifier from WebRTC
- `direction` (string): Track direction (inbound or outbound)
- `kind` (string): Track type (audio or video)

**Relationships:**
- Belongs to one `Session` (many-to-one)
- Belongs to one `Connection` (many-to-one)
- Has many `Events` (one-to-many, stats events)

#### GenericEvent

This model represents all events saved during a call. Events are differentiated by the `category` attribute.

**Fields:**
- `id` (UUID): Unique identifier
- `conference` (FK): The conference this event belongs to
- `participant` (FK): The participant who generated this event
- `peer` (FK, optional): The remote participant (for connection events)
- `session` (FK): The session this event belongs to
- `connection` (FK, optional): The connection this event relates to
- `track` (FK, optional): The track this event relates to
- `app` (FK): The app this event belongs to
- `type` (string): Event type (e.g., 'getUserMedia', 'onicecandidate', 'stats')
- `category` (string): Event category code
- `data` (JSON): Event-specific data
- `created_at` (datetime): When the event occurred

**Event Categories:**
- `B` - Browser events (unload, beforeunload, visibility changes)
- `M` - getUserMedia events (camera/microphone access)
- `C` - Connection events (ICE, signaling, peer connection events)
- `T` - Track events (addTrack, removeTrack)
- `S` - Stats events (WebRTC statistics)

**Relationships:**
- Belongs to one `App` (many-to-one)
- Belongs to one `Conference` (many-to-one)
- Belongs to one `Participant` (many-to-one)
- Optionally belongs to one `Participant` as peer (many-to-one)
- Belongs to one `Session` (many-to-one)
- Optionally belongs to one `Connection` (many-to-one)
- Optionally belongs to one `Track` (many-to-one)

### Model Relationships

The data model follows a hierarchical structure:

```
Organization
    └── App (has api_key)
        ├── Conference (identified by conference_id)
        │   ├── Participants (many-to-many)
        │   ├── Sessions
        │   │   ├── Connections
        │   │   │   └── Tracks
        │   │   └── Events
        │   └── Events
        └── Participants (identified by participant_id)
            ├── Sessions
            └── Events
```

**Key Relationships:**

1. **Organization → App**: One organization can have multiple apps. Each app belongs to one organization.

2. **App → Conference**: One app can have multiple conferences. Each conference belongs to one app and is identified by a user-provided `conference_id`.

3. **Conference ↔ Participant**: Many-to-many relationship. A conference can have multiple participants, and a participant can join multiple conferences.

4. **Participant → Session**: One participant can have multiple sessions in the same conference (if they rejoin). Each session belongs to one participant and one conference.

5. **Session → Connection**: One session can have multiple connections (one per peer). Each connection represents a peer-to-peer link.

6. **Connection → Track**: One connection can have multiple tracks (audio/video, inbound/outbound). Each track belongs to one connection.

7. **Events**: Events are linked to app, conference, participant, session, and optionally to connection and track, depending on the event type.

**Data Flow Example:**

When a user joins a call:
1. SDK calls `/initialize` with `api_key` → validates `App`
2. Creates or retrieves `Conference` (by `conference_id`)
3. Creates or retrieves `Participant` (by `participant_id`)
4. Links `Participant` to `Conference`
5. SDK creates `Session` → links to `Conference` and `Participant`
6. When peer connection is established → creates `Connection`
7. When media tracks are added → creates `Track` entries
8. Continuously sends `Events` (stats, connection state changes, etc.)

### Routes

We can group the routes into 2 categories: **public** (used by the SDK) and **private** (used by web interface to query data).

#### Public

Public endpoints are used by the SDK to send metrics and events. They use JWT token authentication.

- `/initialize`: First endpoint hit by SDK. Validates `api_key` and returns an init token.
  - `POST`
  - Body: `{ apiKey, conferenceId, conferenceName?, userId, userName? }`
  - Returns: `{ token, getStatsInterval, batchConnectionEvents, time }`

- `/sessions`: Manage participant sessions
  - `POST`: Create a new session using init token
    - Body: `{ token, appVersion?, webrtcSdk?, platform?, devices?, constraints?, meta? }`
    - Returns: `{ token }` (session token)
  - `PUT`: Update an existing session using session token
    - Body: `{ token, constraints?, devices?, platform?, webrtcSdk? }`

- `/events/get-user-media`: getUserMedia events (camera/microphone access)
  - `POST`
  - Body: `{ token, data }`

- `/events/browser`: Browser events (unload, page visibility, etc.)
  - `POST`
  - Body: `{ token, type, data }`

- `/connection`: Connection events (SDP, ICE, peer events)
  - `POST`
  - Body: `{ token, type, peerId?, peerName?, connectionId?, data }`

- `/connection/batch`: Batched connection events
  - `POST`
  - Body: `{ token, events: [...] }`

- `/stats`: WebRTC statistics
  - `POST`
  - Body: `{ token, connectionId, data, delta? }`

#### Private

Private endpoints are used by the web interface to query data. They require user authentication.

- `/sessions`: Query participant sessions
  - `GET`, query parameters:
    - `conferenceId`: Get sessions for a specific conference
    - `participantId`: Get sessions for a specific participant
    - `appId`: Get sessions for a specific app

- `/sessions/<uuid:pk>`: Get a specific session
  - `GET`

- `/organizations`: Manage organizations
  - `POST`: Create a new organization
  - `GET`: List user's organizations

- `/organizations/<uuid:pk>`: Manage a specific organization
  - `GET`: Get organization details
  - `PUT`: Update organization
  - `DELETE`: Delete organization

- `/apps`: Manage apps
  - `POST`: Create a new app
  - `GET`: List user's apps

- `/apps/<uuid:pk>`: Manage a specific app
  - `GET`: Get app details
  - `PUT`: Update app
  - `DELETE`: Delete app

- `/conferences`: Query conferences
  - `GET`, query parameters:
    - `appId`: Filter by app
    - `participantId`: Filter by participant

- `/conferences/<uuid:pk>`: Get a specific conference
  - `GET`

- `/conferences/<uuid:pk>/events`: Get all events for a conference
  - `GET`, query parameters:
    - `type`: Filter events by type (e.g., `?type=stats`)

- `/participants`: Query participants
  - `GET`, query parameters:
    - `appId`: Filter by app

- `/participants/<uuid:pk>`: Get a specific participant
  - `GET`

- `/connections`: Query connections
  - `GET`

- `/connections/<uuid:pk>`: Get a specific connection
  - `GET`

- `/issues`: Query issues detected during calls
  - `GET`

- `/issues/<uuid:pk>`: Get a specific issue
  - `GET`

- `/search`: Search across resources
  - `GET`, query parameters:
    - `query`: Search term

## Data Flow

### Metric Ingestion

The SDK continuously sends metrics to the API server during a WebRTC call:

1. **Initialization Phase**
   - SDK calls `/initialize` with API key
   - API validates the key against the `App` model
   - API creates or retrieves `Conference` and `Participant` records
   - API returns an init token (JWT) valid for 24 hours

2. **Session Creation**
   - SDK calls `POST /sessions` with init token
   - API creates a `Session` record with platform, device, and constraint information
   - API returns a session token (JWT) valid for 24 hours
   - Session token is used for all subsequent requests

3. **Event Collection**
   - SDK sends various events using the session token:
     - **getUserMedia events**: When camera/microphone access is requested
     - **Connection events**: When peer connections are created, ICE candidates are gathered, connection state changes
     - **Stats events**: Periodic WebRTC statistics (every 10 seconds by default)
     - **Browser events**: Page visibility changes, unload events
   - Each event is stored as a `GenericEvent` record with appropriate relationships

4. **Connection Tracking**
   - When a peer connection is established, a `Connection` record is created
   - Connection state changes are tracked (new → connecting → connected)
   - Connection type (host, srflx, relay) is detected from stats
   - Negotiation attempts are tracked in `connection_info`

5. **Track Management**
   - When media tracks are added, `Track` records are created
   - Tracks are linked to connections and sessions
   - Stats events for specific tracks are associated with the `Track` record

6. **Session Termination**
   - When the user leaves, SDK sends an unload event
   - API marks all connections as ended
   - API calculates session duration
   - API updates app usage metrics for billing

### Data Storage

Data is organized hierarchically in PostgreSQL:

**Organization Level:**
- Organizations group multiple apps
- Used for access control and billing

**App Level:**
- Each app has a unique API key
- Apps track usage metrics in `durations_days` (JSON field)
- Apps can restrict domains for CORS security

**Conference Level:**
- Conferences group all data for a single call
- Track start time, end time, duration, and ongoing status
- Store conference-level metadata in `conference_info`

**Session Level:**
- Sessions represent a participant's presence in a conference
- Store platform, device, and constraint information
- Track session duration and connection time
- Store custom metadata (up to 5 key-value pairs)

**Connection Level:**
- Connections represent peer-to-peer links
- Track connection type (host, srflx, prflx, relay)
- Store negotiation history in `connection_info`
- Monitor connection state changes

**Track Level:**
- Tracks represent individual media streams
- Differentiate between audio/video and inbound/outbound
- Link stats events to specific tracks

**Event Level:**
- All events are stored as `GenericEvent` records
- Events are categorized (Browser, Media, Connection, Track, Stats)
- Events maintain relationships to all relevant entities
- Stats events can be cleaned up after conference ends (optional)

**Caching:**
- Redis is used to cache frequently accessed objects
- Cache keys are generated based on model fields
- Cache TTL is 1 hour by default
- Improves query performance for active conferences

### Data Querying

The web interface queries data through private endpoints:

**Conference View:**
1. Query conference details: `GET /conferences/{id}`
2. Query all sessions: `GET /sessions?conferenceId={id}`
3. Query all events: `GET /conferences/{id}/events`
4. Filter events by type: `GET /conferences/{id}/events?type=stats`

**Participant View:**
1. Query participant details: `GET /participants/{id}`
2. Query participant sessions: `GET /sessions?participantId={id}`
3. Query conferences: `GET /conferences?participantId={id}`

**Session View:**
1. Query session details: `GET /sessions/{id}`
2. Query connections: `GET /connections?sessionId={id}`
3. Query issues: `GET /issues?sessionId={id}`

**App Dashboard:**
1. Query all conferences: `GET /conferences?appId={id}`
2. Query all participants: `GET /participants?appId={id}`
3. Query all sessions: `GET /sessions?appId={id}`

**Data Retention:**
- Queries are limited to the last 30 days by default
- Older data can be archived or deleted based on retention policy
- Stats events can be cleaned up after conference ends to save storage

**Performance Optimization:**
- Indexes on frequently queried fields (`conference_id`, `participant_id`, `created_at`)
- Redis caching for active conferences and sessions
- Connection pooling for database connections (`CONN_MAX_AGE`)
- Optional batch processing for connection events
