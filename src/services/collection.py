"""Collect configured categories through an API client and raw-page store."""

import asyncio
import json

from infra.collection_store import CollectionStore
from infra.digikala import DigikalaClient
from infra.listing_parser import ListingParser
from schemas.config import CrawlSettings
from schemas.product import PageReference


class CollectionService:
    def __init__(self, settings: CrawlSettings, client: DigikalaClient, store: CollectionStore,
                 parser: ListingParser | None = None):
        self.settings, self.client, self.store = settings, client, store
        self.parser = parser if parser is not None else ListingParser()

    async def run(self) -> dict:
        if self.settings.concurrency < 1 or self.settings.pages_per_category < 0 or self.settings.delay_seconds < 0:
            raise ValueError("Invalid collection limits")
        categories = self.settings.category_ids
        if not categories or len(set(categories)) != len(categories):
            raise ValueError("Configure distinct category IDs")
        self.store.start(self.settings)
        async with self.client:
            self.slots = asyncio.Semaphore(self.client.concurrency)
            async with asyncio.TaskGroup() as group:
                tasks = [group.create_task(self.collect_category(category)) for category in categories]
        return self.store.finish(self.settings, [ref for task in tasks for ref in task.result()])

    async def collect_category(self, category: int) -> list[PageReference]:
        references = []
        async with self.slots:
            page = 1
            while True:
                raw = await self.read_page(category, page)
                listing = self.parser.parse(json.loads(raw), category, page)
                references.append(self.store.reference(category, page, raw))
                limit = listing.total_pages
                if self.settings.pages_per_category:
                    limit = min(limit, self.settings.pages_per_category)
                if page >= limit:
                    return references
                page += 1

    async def read_page(self, category: int, page: int) -> bytes:
        url = self.client.url(category, page)
        raw = self.store.load(category, page)
        if raw is None:
            raw = await self.client.fetch(category, page)
            self.store.save(category, page, raw, url)
        return raw
