"""Records owned by the collection pipeline."""

from dataclasses import dataclass, field


@dataclass
class Attribute:
    name: str
    values: list[str]


@dataclass
class Evidence:
    title: str
    category_title: str | None = None
    description: str | None = None
    alternate_titles: list[str] = field(default_factory=list)
    attributes: list[Attribute] = field(default_factory=list)
    brand: str | None = None


@dataclass
class PageReference:
    category_id: int
    page: int
    file: str
    sha256: str


@dataclass
class Product:
    record_id: str
    source: Evidence
    source_url: str
    category_id: int
    price: int | None
    available: bool | None
    images: list[str]
    observations: list[PageReference]
    currency: str = "IRR"
    normalization_version: str = "digikala-compact/1.0"


@dataclass
class Listing:
    category_id: int
    category_title: str
    page: int
    total_pages: int
    products: list[dict]
