from pydantic import BaseModel, ConfigDict, Field


class EstablishmentCount(BaseModel):
    total: int = 0
    open: int = 0


class HeadOffice(BaseModel):
    siret: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    department: str | None = None
    region: str | None = None
    country: str = "FR"
    latitude: float | None = None
    longitude: float | None = None


class Company(BaseModel):
    model_config = ConfigDict(extra="forbid")

    siren: str
    name: str
    acronym: str | None = None
    status: str
    created_at: str | None = None
    closed_at: str | None = None
    activity_code: str | None = None
    company_category: str | None = None
    employee_band: str | None = None
    establishments: EstablishmentCount
    head_office: HeadOffice


class SearchQuery(BaseModel):
    q: str
    page: int
    page_size: int


class SearchMeta(BaseModel):
    page: int
    page_size: int
    total_results: int
    total_pages: int
    source: str = "API Recherche d’entreprises"


class SearchResponse(BaseModel):
    query: SearchQuery
    meta: SearchMeta
    companies: list[Company] = Field(default_factory=list)
