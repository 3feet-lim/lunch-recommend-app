# Slack Lunch Recommendation Bot Backend

FastAPI MVP scaffold for Slack `/lunch` requests.

## Local setup

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest
```

Required runtime environment variables are documented in `.env.example`. Never commit real Slack,
Naver, Kakao, or OpenWeather credentials.

## Slack endpoints

- `GET /health`
- `POST /slack/commands/lunch`
- `POST /slack/interactions`

Slack request signatures are verified against the raw request body before slash-command parsing.
Valid requests return HTTP 200 immediately and schedule downstream work through FastAPI background
tasks so external providers cannot delay Slack acknowledgement.
