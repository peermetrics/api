# API server

**Note**: this represents a part of the peer metrics WebRTC service. Check out the full project [here](https://github.com/peermetrics/peermetrics).

This folder contains code for the API server used to ingest the metrics sent by the [SDK](https://github.com/peermetrics/sdk-js).

* [How it works](#how-it-works)
* [How to run locally](#how-to-run-locally)
* [Tech stack](#tech-stack)
  * [Models](#models)
        * [Organization](#organization)
        * [App](#app)
        * [Conference](#conference)
        * [Participant](#participant)
        * [Session](#session)
        * [GenericEvent](#genericevent)
  * [Routes](#routes)
        * [Public](#public)
        * [Private](#private)

## How it works

This is a public API endpoint that has two functions:

- ingesting data collected by the SDK
- used for data query by `web`

In addition to this, the api has the django admin interface to check the raw data collected.

## How to run locally

To run this locally check the main [project page](https://github.com/peermetrics/peermetrics).

## Tech stack

- Language: Python 3.8
- Framework: Django
- DB: Postgres

### Models

The main models from this project are:

##### Organization

An organization is pretty much a way to group apps

##### App

Used to group conferences.

##### Conference

The main model for data collection. Used to group: events, sessions and participants

A conference is pretty much a call between participants. A user is encouraged to not reuse `conferece_id`s.

##### Participant

A persona who takes part in a call/conference. You could say this is a user's user.

##### Session

A session is the presence of a participants in a conference. He can have multiple sessions if he joins multiple times.

##### GenericEvent

This model represents all the events that we save during a call. We differentiate between them by the `category` attribute.

### Routes

We can group the routes into 2 categories: **public**  (used by the SDK) and **private** (used accounts to query data for the charts).

##### Public

- `/initialize`: first endpoint hit by SDK. checks that it has a valid `api_key`, etc. returns the token
  - `POST`
- `/events/get-user-media`: gUM events
  - `POST`
- `/events/browser`: browser events: unload, page visibility, etc
  - `POST`
- `/connection`: connection events: sdp, ice, peer events
  - `POST`
- `/connection/batch`: same as previous but accepts batched requests
  - `POST`
- `/stats`: receiving webrtc stats
  - `POST`
- `/sessions`: used to create a participant sessions
  - `POST`: create a new session
  - `PUT`: update a participant's session

##### Private

- `/sessions`: used to get participant sessions
  - `GET`, arguments:
    - `conferenceId`
    - `participantId`
    - `appId`
- `/sessions/<uuid:pk>`: get a specific session
  - `GET`
- `/organizations`: used to get a user's organizations
  - `POST`
- `/organizations/<uuid:pk>`: get a specific org
  - `GET`
  - `PUT`
  - `DELETE`
- `/apps`: get a user's apps
  - - `POST`
- `/apps/<uuid:pk>`
  - `GET`
  - `PUT`
  - `DELETE`
- `/conferences`
  - `GET`, arguments
    - `appId`
    - `participantId`
- `/conferences/<uuid:pk>`
  - `GET`
- `/conferences/<uuid:pk>/events`
  - `GET`  - return all events for a conference
  - arguments (optional):
    - type: filter out events by type. eg: `?type=stats`
- `/participants`
  - `GET` , arguments
    - `appId`
- `/participants/<uuid:pk>`
  - `GET`
- `/search`
  - `GET`, arguments
    - `query`