from typing import Any, Protocol

import httpx


class CompanySearchUpstream(Protocol):
    async def search(self, params: dict[str, Any]) -> dict[str, Any]: ...


class GovernmentCompanyClient:
    BASE_URL = "https://recherche-entreprises.api.gouv.fr"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(8.0),
            headers={"User-Agent": "QServices-FranceCompanyAPI/0.1"},
        )

    async def search(self, params: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.get("/search", params=params)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
