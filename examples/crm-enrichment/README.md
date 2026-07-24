# Mini-project: enrich a CRM CSV

This no-dependency Python script reads a `company_name` column and adds the first matching company’s SIREN, official name, administrative status, postal code, and city.

```bash
export API_BASE_URL='https://YOUR_RAPIDAPI_HOST'
export RAPIDAPI_HOST='YOUR_RAPIDAPI_HOST'
export RAPIDAPI_KEY='YOUR_RAPIDAPI_KEY'
python3 enrich_csv.py sample.csv enriched.csv
```

For local development, omit the RapidAPI variables and use `API_BASE_URL=http://localhost:8000`.

The script deliberately waits 250 ms between rows. It is a small integration example, not a bulk-download tool. Check API-plan quotas before processing a larger file.
