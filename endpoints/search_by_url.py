import sys
import time

sys.path.append('..')
import asyncio
import json
import tldextract
from src.GoogleScraper import GoogleScraper
from src.SkyMemScraper import SkyMemScraper
from src.ContactInfoScraper import ContactInfoScraper, ContactFilter
#from src.MongoDBClient import MongoDBClient
from src.FilteringData import FilteringData
from src.SQLite3Client import SQLiteClient
from src.HTMLFetcher import AsyncHTMLFetcher, HTMLFetcher, PlaywrightPool
from curl_cffi import requests as curl_requests
extract = tldextract.TLDExtract(cache_dir='/tmp')

async_fetcher = None
_fetcher = None

def get_fetcher():
    global _fetcher
    if _fetcher is None:
        _fetcher = PlaywrightPool(size=3)
    return _fetcher

def curl_fetch(url, timeout=10):
    """Fast HTTP fetch using curl_cffi. Returns a Response-like object."""
    try:
        r = curl_requests.get(url, timeout=timeout, impersonate='chrome120', allow_redirects=True)
        return type("Response", (), {"text": r.text, "status_code": r.status_code, "url": str(r.url)})()
    except Exception as e:
        return type("Response", (), {"text": "", "status_code": 0, "url": url})()
#import tracemalloc
#tracemalloc.start()
#import nest_asyncio
#nest_asyncio.apply()
#async def init_async_fetcher():
#    global async_fetcher
#    async_fetcher = AsyncHTMLFetcher()
#    await async_fetcher.init()
#asyncio.get_event_loop().run_until_complete(init_async_fetcher())

google_scraper = GoogleScraper()
skymem_scraper = SkyMemScraper()
contact_scraper = ContactInfoScraper()
filter_data = FilteringData()
#mongo_client = MongoDBClient('contact-scraper-db', 'contact-scraper-companies')
sql_client = SQLiteClient()


# # List of common business domains to filter out
# business_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
#
#
# def is_personal_email(email):
#     """
#     Check if the given email is from a business or non-personal domain.
#     """
#     # Extract the domain part of the email
#     domain = email.split('@')[-1].lower()
#
#     # Return True if the email domain is not a personal email domain
#     return domain not in business_domains

async def process_subpages(fetcher:AsyncHTMLFetcher, contact_scraper:ContactInfoScraper, subpages_links, debug=False):
    async def fetch_and_extract(url):
        try:
            response= await get_fetcher().normal_fetch(url,5000)
            emails, phones , social_media = contact_scraper.get_contact(response.text,url,False)
            return emails, phones, social_media
        except Exception as e:
            return set(), set(), set()


    tasks = [fetch_and_extract(url) for url in subpages_links]
    return await asyncio.gather(*tasks)
def url_compose(url):
    # parsed_url = urlparse(url)
    # if not parsed_url.scheme:
    #     url = urlunparse(('https', parsed_url.netloc, parsed_url.path, '', '', ''))
    #     return url
    if not url.startswith('http'):
        return f"https://{url}"
    return url


def search_by_url(params, debug=True):
    total_start = time.time()
    try:
        # Parameter parsing
        parse_start = time.time()
        url = params.get('url')
        use_db = params.get('use-db', 'true').lower() == 'true'
        realtime = params.get('realtime', 'false').lower() == 'true'
        filter_personal_emails = params.get('filter-personal-emails', 'false').lower() == 'true'
        email_limit = int(params.get('email-limit', 100))
        phone_limit = int(params.get('phone-limit', 100))
        if debug: print(f"Parameter parsing time: {time.time() - parse_start:.2f}s")

        if not url:
            print('400')
            return {"statusCode": 400, "body": json.dumps({"error": "Missing URL in the query parameters"})}

        if response := filter_data.filter_link(url):
            return {"statusCode": 200, "body": json.dumps(response)}

        # URL processing
        url_process_start = time.time()
        if not url.startswith('http'):
            domain = url
            url = url_compose(url)
        else:
            domain = tldextract.extract(url).registered_domain
        if debug: print(f"URL processing time: {time.time() - url_process_start:.2f}s")

        # Database check
        db_check_start = time.time()
        if use_db:
            existing_entry = sql_client.find_entry(domain)
            print(existing_entry)
            if existing_entry:
                existing_entry['emails'] = ContactFilter().emails_filter(existing_entry['emails'],
                                                                         filter_personal_emails)
                existing_entry['emails'] = existing_entry['emails'][:email_limit]
                existing_entry['phones'] = existing_entry['phones'][:phone_limit]
                if debug: print(f"Database lookup time: {time.time() - db_check_start:.2f}s")
                return {'statusCode': 200, 'body': json.dumps(existing_entry)}
        if debug: print(f"Database check time: {time.time() - db_check_start:.2f}s")

        emails_set, phones_set, social_media_set = set(), set(), set()

        # OPTIMIZATION: Try SkyMem first (fastest method)
        if not realtime:
            skymem_start = time.time()
            emails_set = skymem_scraper.scrape_emails(domain, emails_set)
            if debug: print(f"Skymem processing time: {time.time() - skymem_start:.2f}s")

            # If SkyMem found enough emails, skip heavy Playwright scraping
            if len(emails_set) >= 2:
                if debug: print(f"✅ Found {len(emails_set)} emails from SkyMem, skipping Playwright")
                response_data = {
                    'domain': domain,
                    'url': url,
                    'emails': list(emails_set),
                    'phones': [],
                    'status': 'skymem_only'
                }
                # Quick fetch for social media only
                try:
                    response = curl_fetch(url, timeout=8)
                    if response.status_code == 200 and len(response.text) > 500:
                        _, _, social_media, _ = contact_scraper.get_contact(response.text, response.url, True)
                        social_media_set.update(social_media)
                        response_data.update(contact_scraper.group_links_by_platform(domain, social_media_set))
                except:
                    pass

                if use_db:
                    sql_client.insert_entry(response_data)
                response_data.pop('inserted_id', None)
                response_data.pop('_id', None)
                return {'statusCode': 200, 'body': json.dumps(response_data)}

        # Step 1: Try curl_cffi first (fast, reliable for most sites)
        links = set()
        curl_html_len = 0
        try:
            fetch_start = time.time()
            response = curl_fetch(url, timeout=10)
            curl_html_len = len(response.text)
            if debug: print(f"curl_cffi fetch time: {time.time() - fetch_start:.2f}s, status={response.status_code}, len={curl_html_len}")

            if response.status_code in (200, 301, 302) and curl_html_len > 500:
                emails, phones, social_media, links = contact_scraper.get_contact(response.text, response.url, True)
                emails_set.update(emails)
                phones_set.update(phones)
                social_media_set.update(social_media)
                if debug: print(f"curl_cffi found: emails={len(emails_set)}, phones={len(phones_set)}")
        except Exception as e:
            if debug: print(f"curl_cffi failed: {e}")

        # Step 2: If curl didn't find emails AND page looks JS-rendered, try Playwright
        # JS-rendered indicators: curl got small HTML (<5KB), or curl failed entirely
        needs_js = len(emails_set) == 0 and (curl_html_len < 5000 or curl_html_len == 0)
        if needs_js:
            try:
                fetch_start = time.time()
                response = get_fetcher().normal_fetch(url, timeout=10000)
                if debug: print(f"Playwright fetch time: {time.time() - fetch_start:.2f}s, status={response.status_code}, len={len(response.text)}")

                if response.status_code != 404 and len(response.text) > 500:
                    emails, phones, social_media, pw_links = contact_scraper.get_contact(response.text, response.url, True)
                    emails_set.update(emails)
                    phones_set.update(phones)
                    social_media_set.update(social_media)
                    links.update(pw_links)
                    if debug: print(f"Playwright found: emails={len(emails_set)}, phones={len(phones_set)}")
            except Exception as e:
                if debug: print(f"Playwright failed: {e}")

        # Step 3: Subpages processing - curl only (fast), no Playwright
        if len(emails_set) == 0 and links:
            try:
                subpage_start = time.time()
                subpages_links = contact_scraper.subpages_scraper(response, links)
                if subpages_links:
                    if debug: print(f"Found {len(subpages_links)} subpages")
                    for o in list(subpages_links)[:5]:
                        sub_resp = curl_fetch(o, timeout=8)
                        if sub_resp.status_code == 200 and len(sub_resp.text) > 200:
                            emails, phones, social_media = contact_scraper.get_contact(sub_resp.text, sub_resp.url, False)
                            emails_set.update(emails)
                            phones_set.update(phones)
                            social_media_set.update(social_media)
                        if len(emails_set) > 1:
                            break
                    if debug: print(f"Subpages processing time: {time.time() - subpage_start:.2f}s")
            except Exception as exc:
                if debug: print(f"Error processing subpages: {exc}")

        # Step 4: Social media scraping - curl only, Playwright only for Facebook
        if social_media_set and len(emails_set) == 0:
            for social in list(social_media_set)[:3]:
                if len(emails_set) > 0:
                    break
                try:
                    if 'facebook' in social:
                        response = get_fetcher().normal_fetch(social, timeout=8000, facebook=True)
                    else:
                        response = curl_fetch(social, timeout=8)
                    if len(response.text) > 200:
                        emails, phones, social_media = contact_scraper.get_contact(response.text, response.url, False)
                        emails_set.update(emails)
                        phones_set.update(phones)
                    if debug: print(f'Social Media link found: {emails}')
                except Exception as exc:
                    if debug: print(f"Error processing social media links: {exc}")

        # Response construction
        response_build_start = time.time()
        response_data = {
            'domain': domain,
            'url': url,
            'emails': list(emails_set),
            'phones': list(phones_set),
        }
        response_data.update(contact_scraper.group_links_by_platform(domain, social_media_set))
        if debug: print(f"Response construction time: {time.time() - response_build_start:.2f}s")

        # Database insertion
        db_insert_start = time.time()
        
        if use_db and (emails_set or phones_set):
            sql_client.insert_entry(response_data)

        if debug: print(f"Database insertion time: {time.time() - db_insert_start:.2f}s")

        # Data cleanup
        cleanup_start = time.time()
        response_data.pop('inserted_id', None)
        response_data.pop('_id', None)
        response_data['emails'] = response_data['emails'][:email_limit]
        response_data['phones'] = response_data['phones'][:phone_limit]
        if debug: print(f"Data cleanup time: {time.time() - cleanup_start:.2f}s")
        #with open('./html.html', 'w') as f:
        #    f.write(response.text)
        print(f"\nTotal execution time: {time.time() - total_start:.2f}s")
        return {'statusCode': 200, 'body': json.dumps(response_data)}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
