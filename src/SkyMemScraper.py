from curl_cffi import requests
from parsel import Selector
from stealth_requests import StealthSession
class SkyMemScraper:
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Referer': 'https://www.google.com/',
        'Sec-Ch-Ua': '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
    }

    proxies = {

    }

    emails = set()

    def send_request(self, session, link):
        try:
            response = session.get(link, headers=self.headers, proxies=self.proxies, timeout=5)  # Reduced timeout
            return Selector(response.text)
        except Exception as e:
            # Silent fail for speed
            return None

    def scrape_emails(self, domain, emails):
        """Optimized SkyMem scraper with faster timeouts."""
        skymem_url = f'https://www.skymem.info/srch?q={domain}&ss=home'
        try:
            with StealthSession() as session:
                session.proxies.update(self.proxies)
                # Fetch the first page and extract emails
                initial_response = self.send_request(session, skymem_url)
                emails = self.extract_emails(initial_response, emails)

                # Only fetch second page if first page was successful and found emails
                if initial_response and len(emails) > 0:
                    next_page_link = initial_response.css('a[href^="/domain"]::attr(href)').get()
                    if next_page_link:
                        next_page_url = f'https://www.skymem.info/domain/{next_page_link.split("domain/")[-1].split("?p=")[0]}?p=2'
                        next_page_response = self.send_request(session, next_page_url)
                        emails = self.extract_emails(next_page_response, emails)
        except Exception as e:
            # Silent fail - return whatever emails we got
            pass

        return emails

    def extract_emails(self, response, emails):
        if response:
            email_links = response.css('.table-bordered a::text').getall()
            emails.update(email.split('/srch?q=')[-1].split('?p=')[0] for email in email_links)
        return emails
