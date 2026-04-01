# architecture notes

## data flow

1. user starts scrape job from pipeline page
2. backend creates `pipeline_jobs` row
3. background worker runs playwright scraper by brand
4. raw scrape payload saved to `data/raw`
5. normalized rows saved to brands products reviews tables
6. user starts analysis job
7. backend computes sentiment and themes
8. brand metrics and insight cards are generated
9. cleaned csv outputs saved to `data/cleaned`
10. dashboard pages query api routes for live data

## design choices

- fastapi for clear route and service separation
- postgres schema first for reproducibility
- scraper and analysis split into separate jobs
- deterministic fallback for insights when llm fails
- frontend query caching with react query

## why this works for assignment

- covers sentiment, pricing, competitive comparison, and interactive ui
- exposes brand and product drilldown with dynamic filters
- includes agent insight layer with non obvious conclusions
- has cleaned dataset artifact for submission package
