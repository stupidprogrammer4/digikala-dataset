"""Translate the discovery API envelope into a listing record."""

from schemas.product import Listing


class ListingParser:
    def parse(self, payload: dict, category_id: int, page: int) -> Listing:
        if payload.get("status") != 200:
            raise ValueError("Discovery API reported an unsuccessful response")
        listings = [widget["data"] for widget in payload["data"]["widgets"]
                    if widget.get("type") == "vertical_product_listing"]
        if len(listings) != 1:
            raise ValueError("Expected one product listing")
        listing = listings[0]
        category, pager = listing["category"], listing["pager"]
        if category["id"] != category_id or pager["current_page"] != page:
            raise ValueError("API returned a different category or page")
        products = [widget["data"] for widget in listing["widgets"] if widget.get("type") == "product"]
        if not products and pager["total_items"]:
            raise ValueError("Nonempty category returned an empty product page")
        return Listing(category_id, category.get("title_fa") or category["title_en"],
                       page, pager["total_pages"], products)
