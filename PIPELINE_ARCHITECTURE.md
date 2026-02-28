# Capital Architects — Pipeline Architecture

> **Channel:** Capital_Architects | **Audience:** India | **Topic:** Finance  
> **Format:** YouTube Shorts (≤60s, 1080×1920) | **Cadence:** Every 6 hours

---

## System Overview

```
                    ┌───────────────────────────────────────────────┐
                    │       OpenClaw Scheduler (every 6 hours)      │
                    │       Runtime cap: 25 minutes                  │
                    └───────────────────┬───────────────────────────┘
                                        │
                                        ▼
                              run_pipeline.py
                              (Orchestrator)
                                        │
              ┌─────────────────────────┼──────────────────────────────┐
              │           TIME BUDGET CHECK at each stage              │
              │           pipeline aborts gracefully if < 60s left     │
              └─────────────────────────┬──────────────────────────────┘
                                        │
         ════════════════════════ STAGE 1 ═══════════════════════════════

         agents/watchtower.py
         ┌──────────────────────────────────────────────────────────────┐
         │  Parallel-fetch 7 RSS feeds (ThreadPoolExecutor)             │
         │  Sources:                                                     │
         │  ├── RBI Press Releases (Google News geo-targeted)           │
         │  ├── Economic Times Finance                                   │
         │  ├── Bloomberg Asia Finance (Google News)                    │
         │  ├── Government of India PIB                                 │
         │  ├── SEBI Updates (Google News)                              │
         │  ├── India Personal Finance (Google News)                    │
         │  └── India Stock Market (Google News)                        │
         │  Dedup: within-batch hash set + cross-run state.py           │
         │  Output → data/raw/batch_YYYYMMDD_HHMMSS.json               │
         └──────────────────────────────────────────────────────────────┘
                                        │
         ════════════════════════ STAGE 2 ═══════════════════════════════

         agents/prioritizer.py
         ┌──────────────────────────────────────────────────────────────┐
         │  LLM Scoring — OpenRouter (google/gemini-2.0-flash-lite)     │
         │  Up to 25 candidates, 2 workers (rate-limit safe)            │
         │                                                               │
         │  Score dimensions (max 100):                                 │
         │  ┌──────────────────────────┬──────────┐                    │
         │  │ Pocket Impact            │  0–60 pts │                    │
         │  │ Search Intent            │  0–40 pts │                    │
         └──────────────────────────┴──────────┘                    │
         │  Filter: score ≥ 60  |  Select: TOP 5                       │
         │  Output → data/prioritized/selected_stories.json             │
         └──────────────────────────────────────────────────────────────┘
                                        │
         ════════════════════════ STAGE 3 ═══════════════════════════════

         agents/scriptwriter.py
         ┌──────────────────────────────────────────────────────────────┐
         │  GPT-4o via OpenRouter — one call per story                  │
         │  System prompt: prompts/script_system.txt                    │
         │                                                               │
         │  Output JSON (strict):                                       │
         │    project_name:    ≤30 chars                                │
         │    title:           SEO focus, <70 chars                     │
         │    description:     250-350 words + hashtags + specific CTA  │
         │    scenes x5:       (Mandatory 30s-60s length)               │
         │      voice_over:    15–22 words (specific, high-energy)      │
         │      image_prompt:  NO TEXT, metaphorical visual             │
         │      caption.text:  5–8 words                                │
         │    metadata:        source_url, story_hash, topics           │
         │                                                               │
         │  Validation: word counts (5 scenes), no-text checks          │
         │  Output → data/scripts/draft_<hash>.json                     │
         └──────────────────────────────────────────────────────────────┘
                                        │
         ════════════════════════ STAGE 4 ═══════════════════════════════

         agents/judge.py
         ┌──────────────────────────────────────────────────────────────┐
         │  GPT-4o — weighted scoring + rewriting                       │
         │  System prompt: prompts/judge_system.txt                     │
         │                                                               │
         │  Criteria (max 100 pts):                                     │
         │  ┌────────────────────────┬──────────┐                      │
         │  │ Hook Strength          │  20 pts  │                      │
         │  │ Specific Action Value  │  40 pts  │ <--- CRITICAL        │
         │  │ Duration & Depth (5s)  │  20 pts  │                      │
         │  │ Retention Potential    │  10 pts  │                      │
         │  │ SEO & Copy             │  10 pts  │                      │
         │  └────────────────────────┴──────────┘                      │
         │                                                               │
         │  Decision flow (max 3 re-score loops):                       │
         │  score ≥ 85   → APPROVED → data/approved/                   │
         │  60–84        → IMPROVE  → LLM rewrites → rescore           │
         │  score < 60   → REJECT   → data/rejected/                   │
         │  3 loops done → REJECT (human review queue)                  │
         └──────────────────────────────────────────────────────────────┘
                                        │
         ═══════════ PER APPROVED SCRIPT (stages 5–8 loop) ═════════════

         STAGE 5 — agents/imager.py
         ┌──────────────────────────────────────────────────────────────┐
         │  Runware API (async, 3 images concurrent)                    │
         │  1080 × 1920  |  model: runware:100@1                        │
         │  negativePrompt: "text letters watermark captions ..."       │
         │  Retries: 3 with exponential backoff                         │
         │  Output → data/media/<hash>/img_01.png  img_02  img_03       │
         └──────────────────────────────────────────────────────────────┘

         STAGE 6 — agents/voicer.py
         ┌──────────────────────────────────────────────────────────────┐
         │  Primary:  Coqui TTS (local, offline)                        │
         │    Model:   tts_models/en/vctk/vits                          │
         │    Speaker: p326 (male, near-Indian neutral accent)          │
         │    Speed:   1.1× (high-energy finance tone)                  │
         │  Fallback: gTTS (tld=co.in) → WAV via ffmpeg                 │
         │  Output → data/media/<hash>/voice_01.wav  _02  _03           │
         └──────────────────────────────────────────────────────────────┘

         STAGE 7 — agents/stitcher.py
         ┌──────────────────────────────────────────────────────────────┐
         │  FFmpeg + Pillow (for robust captioning)                     │
         │  Per scene:                                                   │
         │    1. Pillow: Draw cinematic captions to transparent PNG      │
         │    2. Scale+Crop image → 1280x2276 (increase for Ken Burns)  │
         │    3. Ken Burns: Zoompan filter (alternating zoom in/out)    │
         │    4. Overlay: Pillow caption PNG + fade transitions         │
         │    5. Duration: Matched to audio length                      │
         │  Concat: ffmpeg concat demuxer                               │
         │  Export: 1080x1920 (Shorts ready), H.264 CRF23 + AAC         │
         │  Output → data/output/<hash>_<name>_final.mp4               │
         └──────────────────────────────────────────────────────────────┘

         STAGE 8 — agents/publisher.py
         ┌──────────────────────────────────────────────────────────────┐
         │  YouTube Data API v3                                         │
         │                                                               │
         │  India traffic peak slots (IST):                             │
         │    7:30 AM  |  12:30 PM  |  6:30 PM  |  9:00 PM             │
         │                                                               │
         │  Collision detection: fetches existing scheduled videos      │
         │  Lookahead: up to 4 days for open slot                       │
         │  Upload: privacyStatus=private + publishAt (UTC ISO)         │
         └──────────────────────────────────────────────────────────────┘
```

---

## Data Directory Map

```
content-generation-pipeline/
│
├── agents/
│   ├── watchtower.py      Stage 1: RSS fetch
│   ├── prioritizer.py     Stage 2: LLM story ranking
│   ├── scriptwriter.py    Stage 3: Script generation
│   ├── judge.py           Stage 4: Weighted scoring + improve
│   ├── imager.py          Stage 5: Runware image generation
│   ├── voicer.py          Stage 6: Coqui TTS voiceover
│   ├── stitcher.py        Stage 7: FFmpeg video assembly
│   └── publisher.py       Stage 8: YouTube upload + scheduling
│
├── pipeline/
│   ├── logger.py          Structured logging (file + console)
│   └── state.py           Persistent run state (JSON on disk)
│
├── prompts/
│   ├── script_system.txt  GPT-4o system prompt (scriptwriter)
│   └── judge_system.txt   GPT-4o system prompt (judge)
│
├── data/                  (gitignored — generated at runtime)
│   ├── raw/               RSS batch files per run
│   ├── prioritized/       top-5 story JSON per run
│   ├── scripts/           LLM draft scripts
│   ├── approved/          Judge-approved scripts
│   ├── rejected/          Rejected scripts
│   ├── media/             Images + audio WAV per story
│   └── output/            Final MP4 Shorts
│
├── logs/                  Daily rotating log files
├── run_pipeline.py        Main orchestrator
├── auth_youtube.py        One-time OAuth2 flow
├── openclaw_task.yaml     OpenClaw scheduler config
├── rerun_approved.py       Manual regeneration utility (skips AI gen)
├── requirements.txt       Python dependencies
└── .env.template          API key template
```

---

## Security Model

| Layer | Control |
|---|---|
| API Keys | `.env` only, gitignored, never hardcoded |
| File access | Project directory only (OpenClaw sandbox) |
| Shell access | Disabled in OpenClaw task config |
| Outbound HTTP | Whitelisted domains only |
| External text | RSS content sanitized before LLM prompt injection |
| YouTube OAuth | Refresh token in `youtube_token.json` (gitignored) |

---

## LLM Cost Estimate Per Run

| Stage | Model | Provider | Cost |
|---|---|---|---|
| Story ranking | `stepfun/step-3.5-flash:free` | OpenRouter | **Free** |
| Script writing | `openai/gpt-4o` | OpenRouter | ~$0.01/script |
| Judge + rewrite | `openai/gpt-4o` | OpenRouter | ~$0.03/loop max |
| Images | `runware:100@1` | Runware | Per image |
| Voiceover | Coqui TTS (local) | Offline | **Free** |

> **Typical cost per video produced: $0.05 – $0.15**

---

## OpenClaw Task Summary

| Setting | Value |
|---|---|
| Trigger | `interval_hours: 6` (internal scheduler) |
| Runtime cap | 25 minutes (+ 23-min self-abort inside orchestrator) |
| First run | 7:00 AM IST |
| Working directory | `/content-generation-pipeline` only |
| Shell access | Disabled |
| Log rotation | Daily, 30-day retention |
| Failure behavior | No auto-retry (next scheduled run starts fresh) |
