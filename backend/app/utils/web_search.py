import httpx
from lxml import html
import logging

logger = logging.getLogger(__name__)

async def search_duckduckgo(query: str, max_results: int = 3) -> list[dict]:
    """
    Perform async web search using DuckDuckGo HTML endpoint.
    Returns a list of dicts with 'title', 'href', 'body'.
    Raises Exception on failure.
    """
    url = "https://html.duckduckgo.com/html/"
    payload = {
        "q": query,
        "b": "",
        "kl": "us-en",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, data=payload, headers=headers)
        if resp.status_code != 200:
            logger.error(f"DuckDuckGo search failed with status {resp.status_code}")
            raise Exception(f"DuckDuckGo search failed with status {resp.status_code}")

        tree = html.fromstring(resp.content)

        results = []
        items = tree.xpath("//div[contains(@class, 'body')]")

        for item in items:
            title_parts = item.xpath(".//h2//text()")
            title = "".join(title_parts).strip()

            hrefs = item.xpath("./a/@href")
            href = hrefs[0] if hrefs else ""

            body_parts = item.xpath("./a//text()")
            body = "".join(body_parts).strip()

            if href.startswith("https://duckduckgo.com/y.js"):
                continue

            results.append({
                "title": title,
                "href": href,
                "body": body
            })

            if len(results) >= max_results:
                break

        return results
