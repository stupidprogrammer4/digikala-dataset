"""HTTP lifecycle and requests for the discovery endpoint."""

import asyncio

import httpx

from schemas.config import CrawlSettings
from infra.listing_parser import ListingParser
from infra.robots import RobotsPolicy


class DigikalaClient:
    def __init__(self, settings: CrawlSettings, *, policy: RobotsPolicy | None = None,
                 parser: ListingParser | None = None, transport=None):
        self.settings = settings
        self.policy = policy if policy is not None else RobotsPolicy(settings.user_agent)
        self.parser = parser if parser is not None else ListingParser()
        self.client = httpx.AsyncClient(timeout=settings.timeout_seconds, transport=transport,
                                       headers={"User-Agent": settings.user_agent})
        self.stopped = asyncio.Event()

    async def __aenter__(self):
        await self.client.__aenter__()
        try:
            await self.policy.load(self.client, self.settings.endpoint)
        except BaseException:
            await self.client.aclose()
            raise
        delay = self.policy.delay
        self.concurrency = 1 if delay else self.settings.concurrency
        self.delay = max(delay, self.settings.delay_seconds)
        return self

    async def __aexit__(self, *args):
        await self.client.__aexit__(*args)

    def url(self, category: int, page: int) -> str:
        url = httpx.URL(self.settings.endpoint.format(category_id=category), params={"page": page})
        try:
            self.policy.check(str(url))
        except PermissionError:
            self.stopped.set()
            raise
        return str(url)

    async def fetch(self, category: int, page: int) -> bytes:
        url = self.url(category, page)
        await asyncio.sleep(self.delay)
        if self.stopped.is_set():
            raise PermissionError("Collection stopped after an access restriction")
        response = await self.client.get(url)
        if response.status_code in (401, 403, 429):
            self.stopped.set()
        response.raise_for_status()
        self.parser.parse(response.json(), category, page)
        return response.content
