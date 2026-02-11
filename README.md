# Databox

Databox gathers data from offline or online sources and exposes a unified REST and GraphQL API using FastAPI.
## Features

### Truth or Dare Endpoint (Games)

This project now includes a simple Truth-or-Dare generator endpoint (REST and GraphQL).

- REST: `GET /v1/truth-or-dare` — query params: `mode`, `game`, `stage`, `notes`, `lang`.
- GraphQL: `truth_or_dare(mode: String, game: String, stage: String, notes: String, lang: String)`

By default the generator uses a small local set of prompts. You can configure an upstream proxy URL with the `DATABOX_TRUTH_DARE_PROXY_URL` environment variable to forward generation to an external service.

Credit / Inspiration
---------------------
This feature was inspired by the Truth-or-Dare API by It-Bulls (api.it-bulls.com). Original description and feature ideas credit go to the original author. Why Choose This API?

💬 Multilingual by Design
Generate truths and dares in 100+ languages — from English, Spanish, and French to Russian, Korean, or Arabic. No manual translation needed. Just pass the lang parameter (full language name) and get localized fun instantly.

🧠 AI-Powered Originality
Each response is generated dynamically by a powerful language model, ensuring unique, natural, and context-appropriate prompts — never repeated, never boring.

🧩 Flexible Customization
Set the context, mood, or theme using the notes field (up to 200 characters):

Add inside jokes or custom scenarios for personal flavor.
Guide tone and style (e.g., “family-safe”, “flirty”, or “wild party”).

❤️ Multiple Relationship or Social Modes
Adapt the experience for any audience:

Date mode: sweet or daring prompts for couples (game=date)
Party mode: fun, silly, or bold challenges for groups (game=party)
Within each game type, select a stage or vibe:

Party: chill, party, wild
Date: new, steady, forever

⚙️ Simple to Use
Just one API call — no sign-up, no setup. Works perfectly for mobile or web games, chatbots, dating apps, and ice-breaker widgets.

Example Request

GET https://api.it-bulls.com/truth-or-dare/v1/truth-or-dare.php?game=party&mode=dare&stage=chill&notes=family%20gathering%20safe%20content&lang=Spanish

Example Response

{
  "ok": true,
  "text": "Tell us about the funniest thing that ever happened during a family dinner!"
}

# Databox

Databox gathers data from offline or online sources and exposes a unified REST and GraphQL API using FastAPI.

![Screenshot](./screenshot.png)

## Quick start

1. Install dependencies:

   `pip install -r requirements.txt`

2. Run the API:

   `uvicorn app.main:app --reload` 

## Docker

Build the image:

`docker build -t databox .`

Run the container:

`docker run --rm -p 8000:8000 databox`

Or with Docker Compose:

`docker compose up --build`

## Endpoints

- REST:
  - GET /v1/health
  - POST /v1/auth/keys
  - GET /v1/data
  - GET /v1/ip/lookup
  - GET /v1/ip/visitor
  - GET /v1/math
  - POST /v1/math
  - GET /v1/site/check
  - GET /v1/password
  - POST /v1/password
  - GET /v1/passphrase
  - POST /v1/passphrase
  - GET /v1/dictionary/en/{word}
  - POST /v1/shamir/secret/split
  - POST /v1/shamir/secret/combine
  - GET /v1/time/now
  - GET /v1/time/utc
  - GET /v1/time/epoch
  - GET /v1/time/convert
  - GET /v1/time/diff
  - GET /v1/time/world
  - GET /v1/time/format
  - GET /v1/time/ntp/status
  - GET /v1/time/leap
  - GET /v1/timezones
  - GET /v1/timezones/abbreviations
  - GET /v1/timezones/offsets
  - GET /v1/timezones/zones
  - GET /v1/timezones/{zone_name}/current
  - GET /v1/timezones/{zone_name}
- GraphQL:
  - POST /v1/graphql

## Authentication

All routes require an API key except `GET /v1/health` and `POST /v1/auth/keys`.
Send the key in the Authorization header:

`Authorization: Bearer db_...`

## Rate limiting and request IDs

- Rate limit: 60 requests/minute per API key (or per client IP when no key is provided).
- If the limit is exceeded, the API returns 429 with `Retry-After`.
- Each response includes `X-Request-Id`. If the client does not send one, the server generates `db_<uuid>`.

## Swagger and OpenAPI

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Configuration

Set these environment variables if needed:

- DATABOX_ENV (default: dev)
- DATABOX_CORS_ORIGINS (default: *)
- DATABOX_LOCAL_DATA_PATH (default: data/sample.json)
- DATABOX_API_KEYS_PATH (default: data/api_keys.json)
- DATABOX_API_KEY_RETENTION_DAYS (default: 90)
- DATABOX_RATE_LIMIT_PER_MINUTE (default: 60)
- DATABOX_LOG_LEVEL (default: INFO)
- DATABOX_NTP_SERVERS (default: time.hixbe.com,time.google.com,time.cloudflare.com)
- DATABOX_NTP_TIMEOUT_SECONDS (default: 2)
- DATABOX_IPINFO_TOKEN (required for IP endpoints)
- DATABOX_IPINFO_LOOKUP_BASE_URL (default: https://ipinfo.io)
- DATABOX_IPINFO_VISITOR_URL (default: https://api.ipinfo.io/lite/me)
- DATABOX_IPINFO_TIMEOUT_SECONDS (default: 5)
- DATABOX_MATH_EVAL_TIMEOUT_SECONDS (default: 10)
- DATABOX_MATH_MAX_EXPR_LENGTH (default: 4096)
- DATABOX_SITE_CHECK_TIMEOUT_CONNECT_SECONDS (default: 3)
- DATABOX_SITE_CHECK_TIMEOUT_READ_SECONDS (default: 5)
- DATABOX_SITE_CHECK_MAX_REDIRECTS (default: 5)
- DATABOX_SITE_CHECK_USER_AGENT (default: databox/1.0 (+https://github.com/anisafifi/databox))
- DATABOX_SITE_CHECK_ALLOWLIST (optional CSV allowlist)
- DATABOX_SITE_CHECK_HEADER_ALLOWLIST (default: content-type,content-length,server,cache-control,location,date)
- DATABOX_PASSWORD_MAX_LENGTH (default: 128)
- DATABOX_DICTIONARY_BASE_URL (default: https://api.dictionaryapi.dev/api/v2/entries)
- DATABOX_DICTIONARY_TIMEOUT_SECONDS (default: 5)
- DATABOX_SERVER_URL (optional OpenAPI server URL)
- DATABOX_HTTP_SOURCE_URL (optional)

## Password presets

Available presets: `strong`, `pin`, `passphrase`.
When `preset` is set, you can still override any option explicitly.

## GraphQL coverage

GraphQL mirrors the REST surface. Key fields include:

- Queries: `health`, `data`, `timeNow`, `timeUtc`, `timeEpoch`, `timeConvert`, `timeDiff`, `timeWorld`, `timeFormat`, `timeNtpStatus`, `timeLeap`, `timezones`, `timezone`, `timezoneCurrent`, `timezoneAbbreviations`, `timezoneOffsets`, `timezoneZones`, `ipLookup`, `ipVisitor`, `math`, `siteCheck`, `password`, `passphrase`, `dictionaryEn`, `shamirSecretSplit`, `shamirSecretCombine`
- Mutations: `issueApiKey`

## External services

This project integrates with third-party services:

- IP info: ipinfo.io (lookup and visitor endpoints)
- Dictionary: dictionaryapi.dev (English entries)
- NTP: time.hixbe.com, time.google.com, time.cloudflare.com

## Contributors

See Git history for contributors. Contributions are welcome.
