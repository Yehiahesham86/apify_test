"""
Apify Actor entry point for Contact Info Scraper.
Reads input, scrapes each URL/domain concurrently (up to 25 workers),
and pushes results to the dataset.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from apify import Actor
from endpoints.search_by_url import search_by_url

MAX_WORKERS = 25


def scrape(url: str, params: dict) -> dict:
    result = search_by_url(params, debug=False)
    body = result.get("body", "{}")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            body = {"raw": body}
    body["_status"] = result.get("statusCode", 200)
    return body


async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}

        urls = actor_input.get("urls", [])
        email_limit = actor_input.get("emailLimit", 10)
        phone_limit = actor_input.get("phoneLimit", 10)
        filter_personal = actor_input.get("filterPersonalEmails", False)
        realtime = actor_input.get("realtime", False)

        if not urls:
            Actor.log.warning("No URLs provided in input.")
            return

        Actor.log.info(f"Starting scrape for {len(urls)} URL(s) with {MAX_WORKERS} concurrent workers.")

        loop = asyncio.get_event_loop()
        semaphore = asyncio.Semaphore(MAX_WORKERS)

        async def scrape_one(entry):
            url = entry if isinstance(entry, str) else entry.get("url", "")
            if not url:
                return

            params = {
                "url": url,
                "use-db": "false",
                "email-limit": str(email_limit),
                "phone-limit": str(phone_limit),
                "filter-personal-emails": str(filter_personal).lower(),
                "realtime": str(realtime).lower(),
            }

            async with semaphore:
                Actor.log.info(f"Scraping: {url}")
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        result = await loop.run_in_executor(executor, scrape, url, params)
                    await Actor.push_data(result)
                    Actor.log.info(f"Done: {url} — {len(result.get('emails', []))} email(s) found.")
                except Exception as exc:
                    Actor.log.error(f"Failed: {url} — {exc}")
                    await Actor.push_data({"url": url, "error": str(exc)})

        await asyncio.gather(*[scrape_one(entry) for entry in urls])
        Actor.log.info("All URLs processed.")


asyncio.run(main())
