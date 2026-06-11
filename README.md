# Black Essence — Automated Black History YouTube Channel

Multi-agent Python system that researches, scripts, produces, and publishes educational Black History YouTube Shorts.

## Architecture

```
Orchestrator (APScheduler 10:00/18:00 daily)
  ├── Research Agent (Brave Search → Gemini 2.0 Flash)
  ├── Scriptwriting Agent (OpenRouter LLM + optimization rules)
  ├── Production Agent
  │   ├── Voiceover Agent (edge-tts → ElevenLabs)
  │   ├── B-ROLL Agent (Pexels → Pixabay → GIPHY)
  │   ├── Video Assembly Agent (MoviePy + Whisper captions)
  │   └── Thumbnail Agent (Stable Diffusion → PIL)
  ├── Telegram Bot (approval HITL)
  └── Publishing Agent (YouTube + TikTok + Instagram)

Optimization Agent (Sunday 08:00) → YouTube Analytics → optimization_rules.json
```

## Quick Start

```bash
cp .env.example .env
# Fill in your API keys
pip install -r requirements.txt
python __main__.py
```

## Deploy to Heroku

```bash
heroku create black-essence
heroku stack:set container -a black-essence

# Set buildpacks (order matters)
heroku buildpacks:add heroku/python -a black-essence
heroku buildpacks:add https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git -a black-essence

# Set environment variables
heroku config:set BRAVE_API_KEY=... -a black-essence
# ... set all env vars from .env.example

# Deploy
git init
heroku git:remote -a black-essence
git add .
git commit -m "Initial deploy"
git push heroku main

# Scale worker (1 dyno = $5/mo hobby)
heroku ps:scale worker=1 -a black-essence
```

## API Keys Required

| Service | Purpose |
|---------|---------|
| Brave Search | Primary research |
| OpenRouter | Gemini 2.0 Flash (research fallback, scripts, optimization) |
| Pexels | Primary stock footage |
| Telegram Bot Token | Human-in-the-loop approval |

## Important Notes

- Brave Search is the **only required** API with free tier; everything else has graceful fallbacks
- On a free/low-credit setup: Brave + OpenRouter free credits + edge-tts (free) = fully functional
- The `analytix` library + YouTube Analytics is optional — the optimization agent uses mock data if unconfigured
- FFmpeg is required for MoviePy; the Heroku buildpack handles this
- Video assembly uses Whisper `base` model — can be changed to `tiny` for speed on the hobby dyno
