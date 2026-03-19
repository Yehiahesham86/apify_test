"""
Apify Actor entry point for Contact Info Scraper.
Reads input, scrapes each URL/domain, and pushes results to the dataset.
"""

import asyncio
import json
from apify import Actor
from endpoints.search_by_url import search_by_url


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

        Actor.log.info(f"Starting scrape for {len(urls)} URL(s).")

        loop = asyncio.get_event_loop()

        for entry in urls:
            url = entry if isinstance(entry, str) else entry.get("url", "")
            if not url:
                continue

            Actor.log.info(f"Scraping: {url}")

            params = {
                "url": url,
                "use-db": "false",
                "email-limit": str(email_limit),
                "phone-limit": str(phone_limit),
                "filter-personal-emails": str(filter_personal).lower(),
                "realtime": str(realtime).lower(),
            }

            try:
                result = await loop.run_in_executor(None, scrape, url, params)
                await Actor.push_data(result)
                Actor.log.info(f"Done: {url} — {len(result.get('emails', []))} email(s) found.")
            except Exception as exc:
                Actor.log.error(f"Failed to scrape {url}: {exc}")
                await Actor.push_data({"url": url, "error": str(exc)})

        Actor.log.info("All URLs processed.")


asyncio.run(main())
