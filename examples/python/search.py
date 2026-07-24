#!/usr/bin/env python3
"""Search a French company through RapidAPI without third-party packages."""

import json
import os
import sys
import urllib.parse
import urllib.request


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "Qonto"
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    url = f"{base_url}/v1/companies/search?{urllib.parse.urlencode({'q': query})}"
    request = urllib.request.Request(url)

    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    rapidapi_host = os.getenv("RAPIDAPI_HOST")
    if rapidapi_key and rapidapi_host:
        request.add_header("X-RapidAPI-Key", rapidapi_key)
        request.add_header("X-RapidAPI-Host", rapidapi_host)

    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.load(response)

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
