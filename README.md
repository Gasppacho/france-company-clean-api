# France Company Clean API

> Search French companies and get a compact, predictable JSON response for CRM enrichment, onboarding, and data cleanup.

France Company Clean API normalizes the official French **API Recherche d’entreprises** response into a stable schema. It intentionally excludes directors and financial records: the MVP focuses on company identity, activity, status, establishment counts, and head-office location.

## Try it in under two minutes

```bash
curl --request GET \
  --url 'https://YOUR_RAPIDAPI_HOST/v1/companies/search?q=Qonto' \
  --header 'x-rapidapi-host: YOUR_RAPIDAPI_HOST' \
  --header 'x-rapidapi-key: YOUR_RAPIDAPI_KEY'
```

Example response (abridged):

```json
{
  "query": {"q": "Qonto", "page": 1, "page_size": 10},
  "meta": {
    "page": 1,
    "page_size": 10,
    "total_results": 1,
    "total_pages": 1,
    "source": "API Recherche d’entreprises"
  },
  "companies": [
    {
      "siren": "819489626",
      "name": "QONTO",
      "status": "active",
      "activity_code": "64.19Z",
      "head_office": {
        "siret": "81948962600047",
        "postal_code": "75009",
        "city": "PARIS",
        "country": "FR"
      }
    }
  ]
}
```

## Use cases

- validate a French company during onboarding;
- enrich a CRM from a company name or SIREN;
- standardize addresses and administrative status;
- match supplier records without parsing a large upstream payload.

## Endpoint

### `GET /v1/companies/search`

| Parameter | Required | Default | Limits | Description |
|---|---:|---:|---:|---|
| `q` | yes | — | 2–100 chars | Company name, SIREN, SIRET, or search text |
| `page` | no | 1 | 1–100 | Results page |
| `page_size` | no | 10 | 1–25 | Results per page |

Useful headers:

- `X-Cache: HIT|MISS` indicates whether the normalized result came from the one-hour origin cache.
- `Cache-Control: public, max-age=300` allows short downstream caching.

### `GET /health`

Public liveness endpoint. A `200` response confirms the API process is ready; it does not guarantee the upstream government source is currently responding.

Interactive OpenAPI documentation is available at `/docs`; the machine-readable contract is at `/openapi.json`.

## Errors

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Check the query parameters and try again.",
    "details": [{"field": "q", "message": "String should have at least 2 characters"}]
  }
}
```

| Status | Code | Meaning |
|---:|---|---|
| 403 | `RAPIDAPI_PROXY_REQUIRED` | The protected origin must be called through RapidAPI |
| 422 | `INVALID_REQUEST` | One or more query parameters are invalid |
| 503 | `SOURCE_UNAVAILABLE` | The official source timed out, rate-limited, or failed |

## Examples

- [Python](examples/python/search.py)
- [JavaScript](examples/javascript/search.mjs)
- [Mini-project: enrich a CRM CSV](examples/crm-enrichment/README.md)

All examples read credentials from environment variables and never embed API keys.

## Data source, freshness, and limits

- Source: [API Recherche d’entreprises](https://recherche-entreprises.api.gouv.fr/docs/), operated from French public data.
- Source limit documented by the provider: up to 7 requests/second per IP and 30 requests/second per ASN; this is a ceiling, not guaranteed capacity.
- Origin cache: one hour; client cache header: five minutes.
- Results exclude non-diffusible companies because the source does.
- This API is not a complete SIRENE database export and should not be used as legal advice or as the sole basis for compliance decisions.
- Individual fields can be absent or delayed at the source. Callers must accept `null` for optional fields.

## Local development

```bash
uv sync
uv run uvicorn france_company_api.app:app --host 0.0.0.0 --port 8000
uv run pytest
uv run ruff check .
```

Docker:

```bash
docker build -t france-company-clean-api .
docker run --rm -p 8000:8000 france-company-clean-api
```

Set `RAPIDAPI_PROXY_SECRET` in production to reject direct origin calls. Never place that value in source control or logs.

## Support

- Product support: `q.services.entreprise@gmail.com`
- Bugs and reproducible feature requests: [GitHub Issues](../../issues)
- Security reports: see [SECURITY.md](SECURITY.md); do not post secrets in an issue.

## Changelog and license

See [CHANGELOG.md](CHANGELOG.md). The code is MIT licensed. Upstream data remains subject to its source terms and is not relicensed by this repository.
