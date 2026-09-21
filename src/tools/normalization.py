"""Normalize explicit listing facts without inferring semantic labels."""

from urllib.parse import urljoin, urlsplit

from schemas.product import Listing
from schemas.product import Attribute, Evidence, PageReference, Product


def normalize_product(item: dict, listing: Listing, reference: PageReference) -> Product:
    identifier, title = item["id"], item["title_fa"]
    if type(identifier) is not int or identifier <= 0 or not isinstance(title, str) or not title.strip():
        raise ValueError("Product requires an ID and title")
    url = urljoin("https://www.digikala.com", item["url"]["uri"])
    parsed = urlsplit(url)
    segments = parsed.path.strip("/").split("/")
    if (parsed.scheme != "https" or parsed.hostname != "www.digikala.com" or parsed.username
            or parsed.password or segments[:2] != ["product", f"dkp-{identifier}"]):
        raise ValueError("Product URL does not match its identity")
    variant = item.get("default_variant") or {}
    price = (variant.get("price") or {}).get("selling_price")
    if type(price) is not int or price < 0:
        price = None
    statuses = {"marketable": True, "out_of_stock": False}
    availability = statuses.get(item.get("status"))
    if variant.get("status") in statuses and statuses[variant["status"]] != availability:
        availability = None
    attributes = [Attribute(theme["label"], [theme["value"]["title"]])
                  for theme in variant.get("themes") or []
                  if isinstance(theme.get("value"), dict) and theme["value"].get("title")]
    alternate = item.get("title_en")
    images = ((item.get("images") or {}).get("main") or {}).get("url") or []
    evidence = Evidence(title=title, category_title=listing.category_title,
                        alternate_titles=[alternate] if isinstance(alternate, str) and alternate.strip() else [],
                        attributes=attributes, brand=(item.get("data_layer") or {}).get("brand"))
    return Product(f"dkp-{identifier}", evidence, url, listing.category_id, price,
                   availability, images, [reference])
