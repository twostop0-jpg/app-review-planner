# Review cleaning (Day 3)

## Why rules (not LLM)

Cleaning is a **deterministic** stage:

- Field normalization
- Empty / low-signal filtering
- Deduplication
- Basic distribution stats

These steps should be reproducible and cheap. Semantic issue discovery stays for the later Moonshot-powered analyze stage.

## Pipeline position

`raw reviews` → **clean** → `reviews_cleaned` + `cleaning_report` → (Day4+) analyze

## What cleaning does

1. **Normalize**
   - Strip HTML tags / collapse whitespace in title & content
   - Clamp/parse rating to 1–5 (invalid → null)
   - Normalize version strings (`Version 8.4.29` → `8.4.29`)
   - Normalize dates to `YYYY-MM-DD` when parseable
   - Lowercase country code

2. **Filter**
   - Drop reviews with missing id
   - Drop empty title+content
   - Conservatively drop very short symbol/emoji-only posts

3. **Deduplicate**
   - Exact duplicate `id`
   - Near-exact duplicate content fingerprint = SHA1(author + title + content), case-insensitive
   - Keep the first occurrence (collection order is most-recent-first for live/sample feeds)

4. **Report**
   - Input/output counts
   - Removed empty / low-signal / duplicate counts
   - Missing field counts
   - Rating histogram
   - Top versions
   - A few duplicate examples for debugging

## API

- Full job: `POST /api/jobs` then inspect `artifacts.cleaning_report`
- Standalone: `POST /api/clean/preview` with `{ "reviews": [ ... ] }`

## Explicit non-goals (Day 3)

- No keyword topic taxonomy
- No LLM summarization
- No PRD / testcase generation
