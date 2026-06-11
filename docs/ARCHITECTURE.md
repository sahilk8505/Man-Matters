# Man Matters Creative Operating System — Architecture

## System Overview

A production-ready Creative Intelligence Platform for Man Matters Meta Ads. Answers:
1. Which creatives work?
2. Why do they work?
3. When do they fatigue?
4. What should we create next?
5. Which new creatives are likely to win before launch?
6. Which competitor patterns should we replicate?

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15.3, TypeScript, TailwindCSS, Recharts, TanStack Table |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL 16 + pgvector (via Supabase) |
| AI | Gemini 2.5 Pro (analysis) + text-embedding-004 (embeddings) |
| Queue | Celery + Redis |
| Storage | Supabase Storage |
| Deployment | Frontend: Vercel / Backend: Railway or Render |

---

## Port Assignment (avoids conflict with competitor-intel)

| Service | Port |
|---------|------|
| Frontend (dev) | 3001 |
| Backend API | 8001 |
| PostgreSQL | 5433 |
| Redis | 6380 |
| Flower (Celery monitor) | 5556 |

---

## Directory Structure

```
man-matters-cos/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routes (auth, creatives, analytics, fatigue, predictions, competitors, genome, insights, sync)
│   │   ├── core/            # Config, DB, security
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── services/        # Business logic engines
│   │   │   ├── fatigue_engine.py      # Multi-dimensional fatigue scoring
│   │   │   ├── prediction_engine.py   # Pre-launch win prediction
│   │   │   ├── creative_analyzer.py   # Gemini 2.5 Pro analysis
│   │   │   ├── embedding_service.py   # Vector embeddings + similarity search
│   │   │   ├── genome_service.py      # Creative genome pattern analysis
│   │   │   ├── insight_generator.py   # AI insight generation
│   │   │   ├── meta_client.py         # Meta Marketing API client
│   │   │   └── competitor_service.py  # Competitor intelligence
│   │   └── workers/         # Celery tasks + scheduler
│   ├── alembic/             # DB migrations
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── app/(dashboard)/ # 8 dashboard pages
│       ├── components/      # Shared UI components
│       ├── lib/             # API client + utilities
│       └── types/           # TypeScript types
├── supabase/migrations/     # SQL schema (run in order)
└── docker-compose.yml
```

---

## Database Schema (Key Tables)

- **products** — 9 Man Matters products (Hair, Wellness, Fitness)
- **creatives** — Master creative table with lifecycle dates
- **creative_metadata** — AI-extracted attributes (narrative, hook, creator, offer, etc.)
- **creative_embeddings** — pgvector 768-dim embeddings for similarity search
- **creative_daily_metrics** — Daily Meta Ads metrics per creative
- **fatigue_scores** — Daily multi-dimensional fatigue scores (0-100)
- **genome_patterns** — Creative building block combinations with performance data
- **narrative_performance** — Per-product narrative performance + lifespan profiles
- **creative_predictions** — Pre-launch win prediction scores
- **competitor_creatives** — Competitor ads from Meta Ad Library
- **insights** — AI-generated strategic insights

---

## Fatigue Engine

**Not based on one metric.** Uses weighted combination of:
- CTR Decay (baseline vs recent)
- CPC Inflation
- CPM Inflation
- ROAS Decay
- CPA Inflation
- Hook Rate Decay (video only)
- Hold Rate Decay (video only)
- Frequency Score
- Conversion Rate Decay

**Format-specific weights:** Reels weight hook/hold rate heavily. Static weights CTR/CPM. Never compared across formats.

**Fatigue Stages:**
- 0–30: Healthy
- 31–60: Watch
- 61–80: Fatiguing
- 81–100: Fatigued

---

## Prediction Engine

Scoring weights for new creative before launch:

| Signal | Weight |
|--------|--------|
| Winner similarity (embedding cosine) | 35% |
| Loser distance (inverse) | 20% |
| Narrative fitness for product | 20% |
| Format fitness for product | 10% |
| Novelty / saturation score | 15% |

Outputs:
- Creative Success Score (0-100)
- Predicted CTR, CPA, ROAS, Lifespan
- Recommendation: Launch Immediately / Caution / Test / Iterate / Avoid

---

## Background Jobs (Celery Beat)

| Task | Schedule |
|------|---------|
| Meta API sync | Every 6 hours |
| Analyze pending creatives | Every 15 minutes |
| Recalculate fatigue | Daily midnight |
| Generate AI insights | Daily 6am |
| Update product benchmarks | Daily 7am |
| Aggregate genome patterns | Daily 7am |

---

## Getting Started

### 1. Database (Supabase or local Docker)

```bash
# Run migrations in order
psql -U postgres -d man_matters_cos -f supabase/migrations/001_extensions_and_enums.sql
psql -U postgres -d man_matters_cos -f supabase/migrations/002_core_tables.sql
psql -U postgres -d man_matters_cos -f supabase/migrations/003_metrics_and_scores.sql
psql -U postgres -d man_matters_cos -f supabase/migrations/004_ai_tables.sql
psql -U postgres -d man_matters_cos -f supabase/migrations/005_functions_and_views.sql
psql -U postgres -d man_matters_cos -f supabase/migrations/006_seed.sql
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# Fill in Google API key, Meta credentials, Supabase credentials

# Option A: Docker Compose (recommended)
docker compose up db redis backend worker scheduler

# Option B: Local (Python 3.12)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8001

npm install
npm run dev   # starts on port 3001
```

### 4. Login

Default credentials (from seed):
- Email: `admin@manmatters.com`
- Password: (set from hashed value in seed — update the hash or register a new user)

---

## Meta MCP Integration

The platform uses the Meta Marketing API directly via the Python `facebook-business` SDK for automated backend syncs. The Claude Meta MCP tools (available in your Claude conversation) can be used interactively to:
- Trigger syncs via `/sync/meta/trigger`
- Inspect ad performance
- Search the Ad Library for competitors

The two systems are complementary — MCP for interactive queries, backend SDK for automated scheduled syncs.

---

## Key Environment Variables

```bash
# Required for AI
GOOGLE_API_KEY=...           # Gemini 2.5 Pro + text-embedding-004

# Required for Meta sync
META_APP_ID=...
META_APP_SECRET=...
META_ACCESS_TOKEN=...
META_AD_ACCOUNT_ID=act_...

# Required for storage
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
```
