import io
import json
import logging
import httpx
from config import MAX_IMAGE_SEARCH

logger = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_HEADERS = {
    "User-Agent": "PresentationMaker/1.0 (https://github.com/presentationmaker; presentationmaker@example.com)"
}


async def search_wikipedia_images(query: str, max_results: int = 3) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Search for pages
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 5,
            }
            resp = await client.get(WIKI_API, params=params, headers=WIKI_HEADERS)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("search", [])
            if not pages:
                return []
            # Get images from the top pages
            page_titles = [p["title"] for p in pages[:3]]
            params = {
                "action": "query",
                "titles": "|".join(page_titles),
                "prop": "pageimages",
                "pithumbsize": 400,
                "format": "json",
            }
            resp = await client.get(WIKI_API, params=params, headers=WIKI_HEADERS)
            resp.raise_for_status()
            data = resp.json()
            pages_data = data.get("query", {}).get("pages", {})
            results = []
            for page_id, page_data in pages_data.items():
                if "thumbnail" in page_data:
                    results.append({
                        "title": page_data.get("title", ""),
                        "url": page_data["thumbnail"]["source"],
                        "thumbnail": page_data["thumbnail"]["source"],
                    })
            return results[:max_results]
    except Exception as e:
        logger.error(f"Wikipedia image search failed: {e}")
        return []


async def search_bing_images(query: str, max_results: int = 3) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            params = {"q": query, "form": "HDRSC2", "first": "1"}
            resp = await client.get(
                "https://www.bing.com/images/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            html = resp.text
            # Extract image URLs from the page
            results = []
            import re
            # Look for image URLs in the page content
            urls = re.findall(r'mediaurl="(https?://[^"]+\.(?:jpg|jpeg|png|gif|webp)[^"]*)"', html)
            for url in urls[:max_results]:
                if url not in [r["url"] for r in results]:
                    results.append({"title": query, "url": url, "thumbnail": url})
            return results
    except Exception as e:
        logger.error(f"Bing image search failed: {e}")
        return []


async def search_images(query: str, max_results: int = MAX_IMAGE_SEARCH) -> list[dict]:
    results = await search_wikipedia_images(query, max_results)
    if results:
        return results
    results = await search_bing_images(query, max_results)
    return results


DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.wikipedia.org/",
}

try:
    from PIL import Image as PILImage
    import io as _io
except ImportError:
    PILImage = None


async def download_image(url: str, max_size_mb: int = 5) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=DOWNLOAD_HEADERS)
            resp.raise_for_status()
            content = resp.content
            if len(content) > max_size_mb * 1024 * 1024:
                logger.warning(f"Image too large: {len(content)} bytes")
                return None
            return content
    except Exception as e:
        logger.error(f"Image download failed: {e}")
        return None


async def download_and_convert(url: str, max_size_mb: int = 5) -> bytes | None:
    raw = await download_image(url, max_size_mb)
    if raw is None:
        return None
    if PILImage is None:
        return raw
    try:
        img = PILImage.open(_io.BytesIO(raw))
        out = _io.BytesIO()
        img.convert("RGB").save(out, format="PNG")
        return out.getvalue()
    except Exception as e:
        logger.warning(f"Image conversion failed, using raw: {e}")
        return raw
