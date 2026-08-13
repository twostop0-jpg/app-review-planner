# Data collection

## Goal

Collect authentic **U.S. App Store** customer reviews for an arbitrary app URL, without hard-coding app-specific findings.

## Primary source (preferred)

Public iTunes Customer Reviews RSS (XML):

```text
https://itunes.apple.com/us/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/xml
```

Why this instead of scraping the visible App Store HTML page:

- It is a dedicated reviews feed, not the marketing/detail webpage DOM.
- It returns structured review fields (id, rating, title, body, author, version, date).
- It supports pagination and an explicit `us` storefront path.

### Observed behavior

- For the assessment example app (`id839285684`), the RSS XML feed currently returns review entries.
- The JSON variant of the same feed may return an empty `entry` list even when XML has data, so this project parses **XML**.
- Feeds are ordered by most recent and may not include the complete historical corpus.

## Fallback source

If RSS returns no entries for an app, the collector falls back to the iTunes MZStore document endpoint:

```text
https://itunes.apple.com/WebObjects/MZStore.woa/wa/viewContentsUserReviews?id={app_id}&pageNumber={n}&sortOrdering=4&onlyLatestVersion=false&type=Purple+Software
```

This is still not “scrape only the public webpage visible cards”; it uses the store review document endpoint and parses review blocks. Limitations:

- Markup can change without notice.
- Parsing is best-effort for title/body alignment.
- Use RSS whenever it returns data.

## Storefront requirement

All live collection requests use the **US** storefront (`/us/` path or US review document).  
`collection_meta.storefront` is recorded as `us`.

## Rate limiting and politeness

- Default max pages: 5 (configurable via `max_pages`, capped at 10).
- Delay between page requests: ~0.8 seconds.
- Custom User-Agent identifies this local assessment client.
- Do not hammer endpoints in tight loops.

## Collection modes

| `source` | Behavior |
|----------|----------|
| `live` | Fetch from US feeds; also refresh cached sample under `data/samples/{app_id}_us_reviews.json` |
| `sample` | Load cached sample only (offline demo) |
| `import` | Load reviewer-provided JSON/CSV via `import_path` |

## Cached sample

File:

```text
data/samples/839285684_us_reviews.json
```

Marked with:

- `cached: true`
- `storefront: us`
- human-readable `note`

Cached samples are for offline interviewer review. They do **not** replace live/import handling for previously unseen inputs when network/config are available.

## Import formats

### JSON

Either a list of review objects, or:

```json
{
  "app_id": "839285684",
  "reviews": [
    {
      "id": "1",
      "rating": 1,
      "title": "Billing issue",
      "content": "Charged after cancel",
      "author": "alex",
      "date": "2026-01-01",
      "version": "8.0.0",
      "country": "us"
    }
  ]
}
```

### CSV

Example file: `data/imports/example_reviews.csv`

Required columns:

- `id`
- `rating`
- `title`
- `content`

Optional:

- `author`, `date`, `version`, `app_id`, `country`

## API usage

- Full pipeline: `POST /api/jobs` with `source=live|sample|import`
- Collect-only preview: `POST /api/collect/preview`

Example job body:

```json
{
  "app_url": "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684",
  "goal": "subscription conversion",
  "source": "sample",
  "max_pages": 3
}
```

## Transparency rules

- If collection fails or returns too little data, the job fails or reports limitations in `collection_meta.limitations`.
- The system does not fabricate reviews.
