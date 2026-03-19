# encoding: utf-8
import subprocess
import time

try:
    import os
    from scrapy import Spider, Request
    from scrapy.crawler import CrawlerProcess
    # import pandas as pd
    from urllib.parse import quote

except ImportError:
    os.system('pip install scrapy pandas scrapy-xlsx')

rapidapi = input("Enter your RapidAPI key: ")
# phone_limit = int(input("Enter phone number limit (e.g. 10): "))
# email_limit = int(input("Enter email limit (e.g. 10): "))
phone_limit = 5
email_limit = 5
filter_personal_emails = input("Filter personal emails? (y/n): ").lower() == 'y'




subprocess.Popen(
    ['app.exe'],
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print('lunching the api!!')
time.sleep(20)

class Spider_Contact_Scraper(Spider):
    name = "contact_scraper"
    BASE_URL = "http://127.0.0.2:49000/search-by-url"
    items = []
    keys = [
        "emails",
        "phones",
        "linkedin",
        "facebook",
        "instagram",
        "twitter",
        "whatsapp",
        "youtube",
        "tiktok",
    ]
    BASE_item = {
        "url": '',
        "domain": ''
    }

    def start_requests(self):

        for key in self.keys:
            for i in range(1, 6):
                self.BASE_item[f'{key}{i}'] = ''

        with open('../search_urls.txt', 'r') as f:
            urls = f.read().splitlines()
            for url in urls:
                if url:
                    yield Request(
                        f"{self.BASE_URL}?use-db=false&url={quote(url)}&phone-limit={phone_limit}&email-limit={email_limit}&filter-personal-emails={filter_personal_emails}",
                        callback=self.parse)

    def parse(self, response):
        data = response.json()
        item = self.BASE_item.copy()

        item["url"] = data.get("url")
        item["domain"] = data.get("domain")
        for key in self.keys:
            for i, value in enumerate(data.get(key, []), 1):
                item[f"{key}{i}"] = value

        yield item

    # def close(self, spider, reason):
    #     df = pd.DataFrame(self.items)
    #     df.to_excel('result-folder/contact_scraper.xlsx', index=False)
    #     self.logger.info(f"{len(self.items)} items scraped.")


if __name__ == "__main__":
    try:
        rate_limit = 20
        Settings = {
            'FEED_EXPORTERS': {

                'xlsx': 'scrapy_xlsx.XlsxItemExporter',
            },

            'FEEDS': {os.path.join('../result-folder', 'contact_scraper.xlsx'): {
                'format': 'xlsx',
            }},
            # 'LOG_LEVEL': 'INFO',
            "DEFAULT_REQUEST_HEADERS": {
                "x-rapidapi-key": rapidapi,
                "x-rapidapi-host": "company-contact-scraper.p.rapidapi.com"
            },
            'DOWNLOAD_DELAY': 0,
            'CONCURRENT_REQUESTS': rate_limit,
            'CONCURRENT_REQUESTS_PER_DOMAIN': rate_limit,
            'HTTPCACHE_ENABLED': False, # should be False
            'HTTPCACHE_IGNORE_HTTP_CODES': [400, 403, 404, 413, 414, 429, 456, 503, 529, 500],
        }
        process = CrawlerProcess(Settings)
        process.crawl(Spider_Contact_Scraper)
        process.start()
    except Exception as e:
        print(f"Error occurred: {e}")

input("Press Enter to exit...")


