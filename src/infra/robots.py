"""Load crawler access and pacing rules using the standard-library parser."""

from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx


class RobotsPolicy:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.rules = RobotFileParser()

    async def load(self, client: httpx.AsyncClient, endpoint: str) -> None:
        origin = urlsplit(endpoint)
        url = f"{origin.scheme}://{origin.netloc}/robots.txt"
        response = await client.get(url)
        rules = RobotFileParser(url)
        if response.status_code == 404:
            rules.parse([])
        else:
            response.raise_for_status()
            rules.parse(response.text.splitlines())
        self.rules = rules

    @property
    def delay(self) -> float:
        delay = self.rules.crawl_delay(self.user_agent) or 0
        rate = self.rules.request_rate(self.user_agent)
        return max(delay, rate.seconds / rate.requests) if rate else delay

    def check(self, url: str) -> None:
        if not self.rules.can_fetch(self.user_agent, url):
            raise PermissionError("robots.txt disallows the category endpoint")
