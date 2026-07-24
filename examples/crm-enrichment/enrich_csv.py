#!/usr/bin/env python3
"""Enrich a CSV containing a `company_name` column with the first API match."""

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


def search(base_url: str, company_name: str) -> dict:
    query = urllib.parse.urlencode({"q": company_name, "page_size": 1})
    request = urllib.request.Request(f"{base_url}/v1/companies/search?{query}")
    key, host = os.getenv("RAPIDAPI_KEY"), os.getenv("RAPIDAPI_HOST")
    if key and host:
        request.add_header("X-RapidAPI-Key", key)
        request.add_header("X-RapidAPI-Host", host)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: enrich_csv.py input.csv output.csv", file=sys.stderr)
        return 2

    source, destination = map(Path, sys.argv[1:])
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    with source.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
        if not rows or "company_name" not in rows[0]:
            raise ValueError("Input CSV must contain at least one row and a company_name column")

    enriched = []
    for index, row in enumerate(rows):
        payload = search(base_url, row["company_name"])
        company = payload["companies"][0] if payload["companies"] else {}
        enriched.append(
            {
                **row,
                "siren": company.get("siren", ""),
                "official_name": company.get("name", ""),
                "status": company.get("status", ""),
                "postal_code": company.get("head_office", {}).get("postal_code", ""),
                "city": company.get("head_office", {}).get("city", ""),
            }
        )
        if index + 1 < len(rows):
            time.sleep(0.25)

    with destination.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=enriched[0].keys())
        writer.writeheader()
        writer.writerows(enriched)
    print(f"Wrote {len(enriched)} enriched rows to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
