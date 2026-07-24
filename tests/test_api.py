from typing import Any

import httpx
from fastapi.testclient import TestClient

from france_company_api.app import create_app


class FakeUpstream:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    async def search(self, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(params)
        return self.payload


def test_health_reports_service_ready() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "france-company-clean-api",
        "version": "0.1.0",
    }


def test_search_returns_compact_stable_company_schema() -> None:
    upstream = FakeUpstream(
        {
            "results": [
                {
                    "siren": "819489626",
                    "nom_complet": "QONTO (QONTO)",
                    "nom_raison_sociale": "QONTO",
                    "sigle": None,
                    "nombre_etablissements": 4,
                    "nombre_etablissements_ouverts": 1,
                    "activite_principale": "64.19Z",
                    "categorie_entreprise": "ETI",
                    "date_creation": "2016-04-04",
                    "date_fermeture": None,
                    "etat_administratif": "A",
                    "tranche_effectif_salarie": "41",
                    "siege": {
                        "siret": "81948962600047",
                        "adresse": "18 RUE DE NAVARIN 75009 PARIS",
                        "code_postal": "75009",
                        "libelle_commune": "PARIS",
                        "departement": "75",
                        "region": "11",
                        "latitude": "48.8798504602074",
                        "longitude": "2.33841034251448",
                    },
                    "dirigeants": [{"nom": "MUST_NOT_LEAK"}],
                    "finances": {"2024": {"ca": 123}},
                }
            ],
            "page": 1,
            "per_page": 10,
            "total_results": 1,
            "total_pages": 1,
        }
    )

    with TestClient(create_app(upstream=upstream)) as client:
        response = client.get("/v1/companies/search", params={"q": "Qonto"})

    assert response.status_code == 200
    assert response.json() == {
        "query": {"q": "Qonto", "page": 1, "page_size": 10},
        "meta": {
            "page": 1,
            "page_size": 10,
            "total_results": 1,
            "total_pages": 1,
            "source": "API Recherche d’entreprises",
        },
        "companies": [
            {
                "siren": "819489626",
                "name": "QONTO",
                "acronym": None,
                "status": "active",
                "created_at": "2016-04-04",
                "closed_at": None,
                "activity_code": "64.19Z",
                "company_category": "ETI",
                "employee_band": "41",
                "establishments": {"total": 4, "open": 1},
                "head_office": {
                    "siret": "81948962600047",
                    "address": "18 RUE DE NAVARIN 75009 PARIS",
                    "postal_code": "75009",
                    "city": "PARIS",
                    "department": "75",
                    "region": "11",
                    "country": "FR",
                    "latitude": 48.8798504602074,
                    "longitude": 2.33841034251448,
                },
            }
        ],
    }
    assert upstream.calls == [
        {"q": "Qonto", "page": 1, "per_page": 10, "minimal": True, "include": "siege"}
    ]


def test_search_caches_identical_requests() -> None:
    upstream = FakeUpstream(
        {
            "results": [],
            "page": 1,
            "per_page": 10,
            "total_results": 0,
            "total_pages": 0,
        }
    )

    with TestClient(create_app(upstream=upstream)) as client:
        first = client.get("/v1/companies/search", params={"q": "Qonto"})
        second = client.get("/v1/companies/search", params={"q": "Qonto"})

    assert first.status_code == 200
    assert first.headers["x-cache"] == "MISS"
    assert second.headers["x-cache"] == "HIT"
    assert len(upstream.calls) == 1


def test_search_returns_safe_error_when_source_times_out() -> None:
    class TimedOutUpstream:
        async def search(self, params: dict[str, Any]) -> dict[str, Any]:
            request = httpx.Request("GET", "https://source.example/search")
            raise httpx.ReadTimeout("internal source details", request=request)

    with TestClient(create_app(upstream=TimedOutUpstream())) as client:
        response = client.get("/v1/companies/search", params={"q": "Qonto"})

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert response.json() == {
        "error": {
            "code": "SOURCE_UNAVAILABLE",
            "message": "The French company data source is temporarily unavailable. Retry shortly.",
        }
    }
    assert "internal source details" not in response.text


def test_search_validation_error_has_stable_shape() -> None:
    upstream = FakeUpstream({})

    with TestClient(create_app(upstream=upstream)) as client:
        response = client.get("/v1/companies/search", params={"q": "x", "page_size": 999})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "INVALID_REQUEST"
    assert payload["error"]["message"] == "Check the query parameters and try again."
    assert {item["field"] for item in payload["error"]["details"]} == {"q", "page_size"}
    assert upstream.calls == []


def test_search_maps_source_http_error_without_leaking_body() -> None:
    class RateLimitedUpstream:
        async def search(self, params: dict[str, Any]) -> dict[str, Any]:
            request = httpx.Request("GET", "https://source.example/search")
            source_response = httpx.Response(429, request=request, text="private source body")
            raise httpx.HTTPStatusError(
                "source rejected request",
                request=request,
                response=source_response,
            )

    with TestClient(create_app(upstream=RateLimitedUpstream())) as client:
        response = client.get("/v1/companies/search", params={"q": "Qonto"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert "private source body" not in response.text


def test_configured_proxy_secret_blocks_direct_origin_calls() -> None:
    upstream = FakeUpstream(
        {"results": [], "page": 1, "per_page": 10, "total_results": 0, "total_pages": 0}
    )

    with TestClient(create_app(upstream=upstream, proxy_secret="expected-secret")) as client:
        blocked = client.get("/v1/companies/search", params={"q": "Qonto"})
        allowed = client.get(
            "/v1/companies/search",
            params={"q": "Qonto"},
            headers={"X-RapidAPI-Proxy-Secret": "expected-secret"},
        )

    assert blocked.status_code == 403
    assert blocked.json() == {
        "error": {
            "code": "RAPIDAPI_PROXY_REQUIRED",
            "message": "Subscribe and call this endpoint through RapidAPI.",
        }
    }
    assert allowed.status_code == 200
    assert len(upstream.calls) == 1
