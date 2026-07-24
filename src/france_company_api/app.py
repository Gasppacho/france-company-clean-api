import hmac
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from france_company_api import __version__
from france_company_api.cache import TTLCache
from france_company_api.models import (
    Company,
    EstablishmentCount,
    HeadOffice,
    SearchMeta,
    SearchQuery,
    SearchResponse,
)
from france_company_api.upstream import CompanySearchUpstream, GovernmentCompanyClient


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _normalize_company(raw: dict[str, Any]) -> Company:
    office = raw.get("siege") or {}
    return Company(
        siren=str(raw.get("siren") or ""),
        name=raw.get("nom_raison_sociale") or raw.get("nom_complet") or "Unknown",
        acronym=raw.get("sigle"),
        status="active" if raw.get("etat_administratif") == "A" else "closed",
        created_at=raw.get("date_creation"),
        closed_at=raw.get("date_fermeture"),
        activity_code=raw.get("activite_principale"),
        company_category=raw.get("categorie_entreprise"),
        employee_band=raw.get("tranche_effectif_salarie"),
        establishments=EstablishmentCount(
            total=raw.get("nombre_etablissements") or 0,
            open=raw.get("nombre_etablissements_ouverts") or 0,
        ),
        head_office=HeadOffice(
            siret=office.get("siret"),
            address=office.get("adresse"),
            postal_code=office.get("code_postal"),
            city=office.get("libelle_commune"),
            department=office.get("departement"),
            region=office.get("region"),
            latitude=_number(office.get("latitude")),
            longitude=_number(office.get("longitude")),
        ),
    )


def create_app(
    upstream: CompanySearchUpstream | None = None,
    proxy_secret: str | None = None,
) -> FastAPI:
    owns_upstream = upstream is None
    service = upstream or GovernmentCompanyClient()
    configured_proxy_secret = proxy_secret or os.getenv("RAPIDAPI_PROXY_SECRET")
    cache = TTLCache(ttl_seconds=3600, max_entries=1024)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_upstream and isinstance(service, GovernmentCompanyClient):
            await service.close()

    app = FastAPI(
        title="France Company Clean API",
        version=__version__,
        description=(
            "Search French companies and receive a compact, stable JSON schema. "
            "Data source: API Recherche d’entreprises (French government open data)."
        ),
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def require_rapidapi_proxy(request: Request, call_next: Any) -> Response:
        if request.url.path.startswith("/v1/") and configured_proxy_secret:
            supplied = request.headers.get("X-RapidAPI-Proxy-Secret", "")
            if not hmac.compare_digest(supplied, configured_proxy_secret):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "RAPIDAPI_PROXY_REQUIRED",
                            "message": "Subscribe and call this endpoint through RapidAPI.",
                        }
                    },
                )
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            {"field": str(item["loc"][-1]), "message": item["msg"]}
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Check the query parameters and try again.",
                    "details": details,
                }
            },
        )

    def source_unavailable_response() -> JSONResponse:
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "5"},
            content={
                "error": {
                    "code": "SOURCE_UNAVAILABLE",
                    "message": (
                        "The French company data source is temporarily unavailable. Retry shortly."
                    ),
                }
            },
        )

    @app.exception_handler(httpx.RequestError)
    async def source_request_error(_: Request, __: httpx.RequestError) -> JSONResponse:
        return source_unavailable_response()

    @app.exception_handler(httpx.HTTPStatusError)
    async def source_status_error(_: Request, __: httpx.HTTPStatusError) -> JSONResponse:
        return source_unavailable_response()

    @app.get("/health", tags=["Operations"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "france-company-clean-api",
            "version": __version__,
        }

    @app.get(
        "/v1/companies/search",
        response_model=SearchResponse,
        tags=["Companies"],
        summary="Search and normalize French companies",
    )
    async def search_companies(
        response: Response,
        q: str = Query(min_length=2, max_length=100, examples=["Qonto"]),
        page: int = Query(default=1, ge=1, le=100),
        page_size: int = Query(default=10, ge=1, le=25),
    ) -> SearchResponse:
        params = {
            "q": q,
            "page": page,
            "per_page": page_size,
            "minimal": True,
            "include": "siege",
        }
        payload, cache_hit = await cache.get_or_load(
            (q.casefold(), page, page_size),
            lambda: service.search(params),
        )
        response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
        response.headers["Cache-Control"] = "public, max-age=300"
        return SearchResponse(
            query=SearchQuery(q=q, page=page, page_size=page_size),
            meta=SearchMeta(
                page=payload.get("page", page),
                page_size=payload.get("per_page", page_size),
                total_results=payload.get("total_results", 0),
                total_pages=payload.get("total_pages", 0),
            ),
            companies=[_normalize_company(item) for item in payload.get("results", [])],
        )

    return app


app = create_app()
