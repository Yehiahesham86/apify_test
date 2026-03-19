import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from endpoints.search_by_url import search_by_url as search_by_url_sync
from endpoints.search_by_domain import search_by_domain as search_by_domain_sync
import uvicorn
import httpx
# required to be installed using pyinstaller
import re
from urllib.parse import unquote
from email_scraper import scrape_emails
import time
from curl_cffi import requests
from pymongo import MongoClient
from parsel import Selector
from concurrent.futures import ThreadPoolExecutor
import tldextract
import phonenumbers
from html2text import HTML2Text


# ------------
# FASTAPI APP
# ------------
app = FastAPI()

# We’ll create a global thread pool for blocking endpoints
executor = ThreadPoolExecutor(max_workers=5)

RAPID_API_URL = "https://company-contact-scraper.p.rapidapi.com/search-by-url?local_run=true"

# We'll store our shared httpx client
http_client = httpx.AsyncClient(timeout=20)


# ------------
# HELPER FUNCTIONS
# ------------

async def search_by_url(params, debug=False):
    """
    Async function that offloads the blocking search_by_url_sync to thread pool.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, search_by_url_sync, params, debug)

async def search_by_domain(params, debug=False):
    """
    Async function that offloads the blocking search_by_domain_sync to thread pool.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, search_by_domain_sync, params, debug)

async def ping_rapidapi_required(headers: dict):
    """
    Make a synchronous request to RapidAPI. If it fails, raise an exception.
    """
    # We do NOT catch exceptions here so it bubbles up and we can handle it upstream.
    r = await http_client.get(RAPID_API_URL, headers=headers)
    r.raise_for_status()
    print(f"Pinged RapidAPI: {r.status_code}")


async def add_credit_headers(response: dict, request: Request):
    """
    - First, attempts the RapidAPI request (blocking).
    - If that fails, returns a 500 error instead of normal data.
    - Otherwise, returns the normal JSON response with the credit headers.
    """
    body, credits = parse_response_and_credits(response)

    # Grab required request headers
    forwarded_headers = {
        "x-rapidapi-key": request.headers.get("x-rapidapi-key", "883ee94e4fmsh5abbd58d55db971p14b3f2jsn6ecdd4677b44"),
        "x-rapidapi-host": request.headers.get("x-rapidapi-host", "company-contact-scraper.p.rapidapi.com")
    }

    # --- BLOCK on the RapidAPI request before returning the result ---
    try:
        await ping_rapidapi_required(forwarded_headers)
    except Exception as exc:
        # If any error occurs (connection, 4xx/5xx, etc.), we return an error response
        print(f"Error contacting RapidAPI: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "message": "An error occurred contacting RapidAPI. Please try again later.",
                "detail": str(exc),
            },
            headers={"X-RapidAPI-Billing": "Credits=0"}
        )
    # --- If we reach here, RapidAPI call was successful ---

    return JSONResponse(
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-RapidAPI-Billing": f"Credits={credits}"
        },
        status_code=response.get("statusCode", 200)
    )


def parse_response_and_credits(response: dict) -> (dict, int):
    """
    Return the final JSON body and credits used, based on statusCode.
    """
    status_code = response.get("statusCode", 200)
    body = response.get("body", {})
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except:
            # If body isn't valid JSON, fallback to the raw string
            body = {"data": body}

    total_credits = 1 if status_code == 200 else 0
    return body, total_credits



# ------------
# ROUTES
# ------------
@app.get("/")
async def root():
    return {"message": "Welcome to Contact API!"}

@app.get("/search-by-url")
async def handle_url(request: Request, url: str = None, domain: str = None, local_run: str = None):
    params = {"url": url, "domain": domain}
    url_valid = url and url.startswith("http")
    domain_valid = domain and not domain.startswith("http")

    # Param swapping logic
    if url and not url_valid:
        params["domain"] = url
        params.pop("url", None)
        url_valid = False
        domain_valid = True
    elif domain and domain.startswith("http"):
        params["url"] = domain
        params.pop("domain", None)
        url_valid = True
        domain_valid = False

    # Now pick which endpoint to call
    if url_valid:
        response = await search_by_url(params, False)
    elif domain_valid:
        response = await search_by_domain(params, False)
    else:
        response = {"statusCode": 400, "body": {"error": "Invalid parameters"}}

    # Skip RapidAPI billing ping for local runs
    if local_run:
        body, credits = parse_response_and_credits(response)
        return JSONResponse(content=body, status_code=response.get("statusCode", 200))
    return await add_credit_headers(response, request)


@app.exception_handler(Exception)
async def handle_exception(request: Request, exc: Exception):
    print(f"An error occurred: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": f"An error occurred. Please try again later.\n{str(exc)}"},
        headers={"X-RapidAPI-Billing": "Credits=0"}
    )


# ------------
# MAIN ENTRY
# ------------
if __name__ == "__main__":
    # Using multiple workers for better performance (commented out):
    # uvicorn.run("app:app", host="127.0.0.1", port=49000, workers=4)
    # That approach expects "app.py" -> "app" if you do "app:app".

    # Instead, just run the app object directly in single process mode:
    uvicorn.run("app:app", host="127.0.0.2", port=49000, log_level="info")
