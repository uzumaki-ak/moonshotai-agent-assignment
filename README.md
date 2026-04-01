# moonshot ai agent internship assignment

this project builds a competitive intelligence dashboard for luggage brands on amazon india.
it includes scraping, sentiment and theme analysis, brand benchmarking, and an interactive dashboard.

## what is built

- fastapi backend with route based modules
- playwright scraper for amazon india product and review pages
- sentiment scoring with vader plus rating blend
- aspect theme extraction for praise and complaints
- multi llm fallback router
  - openrouter gemini 2.5 flash first
  - groq second
  - euron on openrouter third
  - local ollama qwen fallback
- brand comparison and value for money metrics
- agent insights endpoint
- react dashboard with dynamic filters and drilldowns
- cleaned dataset export as csv

## project structure

```text
backend/
  app/
    api/v1/endpoints/
    core/
    db/
    models/
    schemas/
    services/
  scripts/
  sql/schema.sql
frontend/
  src/
data/
  raw/
  cleaned/
docs/
```

## api routes

- `GET /api/v1/health`
- `GET /api/v1/overview`
- `GET /api/v1/brands`
- `GET /api/v1/brands/compare`
- `GET /api/v1/brands/{brand_id}`
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/reviews`
- `GET /api/v1/insights/agent`
- `POST /api/v1/jobs/scrape`
- `POST /api/v1/jobs/analyze`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`

## frontend routes

- `/` overview
- `/compare` brand comparison
- `/brands/:brandId` brand drilldown
- `/products/:productId` product drilldown
- `/insights` agent insight cards
- `/pipeline` run scrape and analysis jobs

## local setup

### 1 backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
```

update `backend/.env` with your keys and db url.

### 2 database setup option a local postgres

create db first, then run:

```powershell
psql -U postgres -d moonshot_ai -f sql/schema.sql
```

set in `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/moonshot_ai
```

### 3 database setup option b supabase

- create a supabase project
- use transaction sql editor and paste `backend/sql/schema.sql`
- set connection string in `.env`

example:

```env
DATABASE_URL=postgresql+psycopg://postgres.<project_ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

### 4 run backend

```powershell
uvicorn app.main:app --reload --port 8000
```

### 5 frontend setup

```powershell
cd ../frontend
npm install
Copy-Item .env.example .env
npm run dev
```

frontend default is `http://localhost:5173` and backend default is `http://localhost:8000`.

## pipeline usage

### from ui

open `/pipeline` route and:
- enter brands
- start scrape
- then run analysis

### from cli

```powershell
cd backend
python -m scripts.run_pipeline scrape --brands Safari Skybags "American Tourister" VIP --products-per-brand 10 --reviews-per-product 50
python -m scripts.run_pipeline analyze
```

## sentiment and theme method

- review sentiment combines text compound score and star rating signal
- sentiment labels: positive neutral negative
- theme extraction uses aspect keywords and sentiment polarity
- aspects include wheels handle material zipper size durability value delivery

## llm fallback chain

set this in `.env`:

```env
LLM_CHAIN=gemini,groq,euron,local
```

keys used:

```env
OPENROUTER_API_KEY=
GROQ_API_KEY=
```

local fallback requires ollama running with qwen model.

## security notes

- no api keys in frontend
- `.env` is git ignored
- backend only reads keys from env
- raw and cleaned datasets are not committed by default

## submission checklist

- run scrape and analysis
- verify overview and compare pages show real data
- export cleaned csv from `data/cleaned`
- include loom walkthrough explaining pipeline and tradeoffs
- add screenshots and architecture note

## limitations you should mention honestly

- amazon anti bot behavior can reduce scrape yield on some runs
- review availability varies by product
- sentiment is hybrid and not a full domain tuned transformer model
- llm insight generation quality depends on data coverage
