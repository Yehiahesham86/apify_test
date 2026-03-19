import time
import os
import asyncio
import threading
import concurrent.futures

try:
    from patchright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    from patchright.async_api import async_playwright

except ImportError:
    os.system("pip install patchright")
    from patchright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    from patchright.async_api import async_playwright


print("[INFO] Using Patchright (optimized Playwright)")
USING_PATCHRIGHT = True


class AsyncHTMLFetcher:
    """Async version of HTMLFetcher — uses Patchright if available."""

    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    async def init(self):
        """Initialize async Patchright/Playwright and browser context."""
        if self.playwright:
            return
        print(f"[AsyncFetcher] Starting browser ({'Patchright' if USING_PATCHRIGHT else 'Playwright'})...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(ignore_https_errors=True)
        print("[AsyncFetcher] Browser ready.")

    async def normal_fetch(self, url, timeout=10000,):
        """Fetch a page asynchronously without hanging forever."""
        page = await self.context.new_page()
        print('URL for ',url)
        try:
            # Abort unnecessary resource types early
            await page.route("**/*.{png,jpg,jpeg,gif,css,js,woff,woff2,svg,mp4,avi}*", lambda route: route.abort())
            #print('Finished Routing for ',url)
            # Hard timeout wrapper so it never hangs indefinitely
            try:
                await asyncio.wait_for(
                    page.goto(url, wait_until="load", timeout=timeout),
                    timeout=timeout / 1000 + 5,  # total timeout (seconds)
                )
                print('Went for a page ', url)
            except asyncio.TimeoutError:
                print(f"[AsyncFetcher] ⚠️ Hard timeout for {url}")
            except PlaywrightTimeout:
                print(f"[AsyncFetcher] ⚠️ Playwright timeout at {url}")

            # Always try to get content, even if partial
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")

            await asyncio.sleep(2)
            html = await page.content()
            print('HTML ready for ',url)
            return type("Response", (), {"text": html, "status_code": 200, "url": url})()

        except Exception as e:
            print(f"[AsyncFetcher] ❌ Error fetching {url}: {e}")
            return type("Response", (), {"text": "", "status_code": 500, "url": url})()
        finally:
            try:
                await page.close()
            except Exception:
                pass

    async def close(self):
        """Gracefully stop async Playwright."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        finally:
            self.browser = self.context = self.playwright = None
class HTMLFetcher:
    """Thread-safe Playwright fetcher. All browser ops run on a single dedicated thread."""

    def __init__(self, headless=True, restart_every=200):
        self.headless = headless
        self.restart_every = restart_every
        self._playwright = None
        self.browser = None
        self.context = None
        self.fetch_count = 0
        # Single-thread executor: all Playwright calls go here (greenlet requirement)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="pw")
        # Init browser on the dedicated thread
        self._executor.submit(self._init_browser).result()

    def _init_browser(self):
        """Start Patchright/Playwright. Must run on the dedicated thread."""
        self.fetch_count = 0
        if self._playwright:
            return
        print("[Fetcher] Starting browser...")
        self._playwright = sync_playwright().start()

        launch_args = [
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "--disable-default-apps",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-client-side-phishing-detection",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-blink-features=AutomationControlled",
            "--blink-settings=imagesEnabled=false",
            "--disk-cache-size=1",
            "--media-cache-size=1",
            "--aggressive-cache-discard",
            "--disable-application-cache",
            "--disable-breakpad",
            "--disable-component-extensions-with-background-pages",
            "--disable-features=TranslateUI,BlinkGenPropertyTrees",
            "--disable-ipc-flooding-protection",
            "--disable-hang-monitor",
            "--disable-prompt-on-repost",
            "--disable-domain-reliability",
            "--disable-features=AudioServiceOutOfProcess,IsolateOrigins,site-per-process",
            "--disable-features=VizDisplayCompositor",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            "--force-color-profile=srgb",
            "--metrics-recording-only",
            "--no-first-run",
            "--password-store=basic",
            "--use-mock-keychain",
            "--disable-accelerated-2d-canvas",
            "--disable-accelerated-video-decode",
        ]

        self.browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )

        self.context = self.browser.new_context(
            ignore_https_errors=True,
            java_script_enabled=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )

        self.context.route("**/*", lambda route: route.abort() if route.request.resource_type in
            ["image", "media", "font", "stylesheet"]
            else route.continue_())

        print(f"[Fetcher] Browser ready ({'Patchright' if USING_PATCHRIGHT else 'Playwright'}).")

    def _ensure_alive(self):
        """Recreate browser if it crashed. Must run on dedicated thread."""
        try:
            _ = self.context.pages
        except Exception:
            print("[Fetcher] Browser crashed — restarting...")
            self._close_internal()
            self._init_browser()

    def _close_internal(self):
        """Close browser resources. Must run on dedicated thread."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self.browser = self.context = self._playwright = None

    def _fetch_on_thread(self, url, timeout, facebook):
        """The actual fetch — runs entirely on the single Playwright thread."""
        self._ensure_alive()
        self.fetch_count += 1
        if self.fetch_count >= self.restart_every:
            print(f"[Fetcher] Restarting Chromium after {self.fetch_count} fetches to free memory...")
            self._close_internal()
            self._init_browser()

        page = self.context.new_page()

        if not USING_PATCHRIGHT:
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)

        final_url = url
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)

            if facebook:
                try:
                    locator = page.locator('xpath=.//div[@data-pagelet="ProfileTilesFeed_0"]')
                    locator.wait_for(state='visible', timeout=5000)
                except:
                    pass
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            except:
                pass
            time.sleep(0.5)
            html = page.content()
            final_url = page.url
            status = 200
        except PlaywrightTimeout:
            print(f"[Fetcher] Timeout: {url}")
            try:
                html = page.content()
                final_url = page.url
                status = 200 if len(html) > 500 else 408
            except Exception:
                html, status = "", 408
        except Exception as e:
            print(f"[Fetcher] Error: {e}")
            html, status = "", 500
        finally:
            try:
                page.close()
            except Exception:
                pass

        return type("Response", (), {"text": html, "status_code": status, "url": final_url})()

    def normal_fetch(self, url, timeout=10000, facebook=False):
        """Thread-safe: submits fetch to the dedicated Playwright thread and waits."""
        future = self._executor.submit(self._fetch_on_thread, url, timeout, facebook)
        return future.result(timeout=timeout / 1000 + 15)

    def close(self):
        """Gracefully stop Playwright on the dedicated thread."""
        try:
            self._executor.submit(self._close_internal).result(timeout=10)
        except Exception:
            pass


class PlaywrightPool:
    """Pool of HTMLFetcher instances for parallel Playwright fetches."""

    def __init__(self, size=3, headless=True):
        print(f"[Pool] Creating {size} Playwright workers...")
        self._workers = [HTMLFetcher(headless=headless) for _ in range(size)]
        self._index = 0
        self._lock = threading.Lock()
        print(f"[Pool] {size} workers ready.")

    def normal_fetch(self, url, timeout=10000, facebook=False):
        with self._lock:
            worker = self._workers[self._index % len(self._workers)]
            self._index += 1
        return worker.normal_fetch(url, timeout, facebook)

    def close(self):
        for w in self._workers:
            w.close()
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
        'Host': 'www.theamericanlaundromat.com',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
    }
                

if __name__ == '__main__':
    urls = [
        # 'https://101collisioncenter.com',
        # 'https://25thstreetautomotive.com',
        # 'https://3aautorepair.com',
        # 'https://a-aautorepairs.com',
        # 'https://3dbodybusiness.site',
        # 'https://onestopcarrepair.com',
        # 'https://101collisioncenter.com',
        # 'https://1492coachworks.com',
        # 'https://1stchoicecollision.com',
        # 'https://1stclassauto.com',
        # 'https://2brotherscollision.com',
        # 'https://25thstreetautomotive.com',
        # 'https://3aautorepair.com',
        # 'https://3acollision.com',
        # 'https://3dbodybusiness.site',
        # 'https://www.binance.com/ar/404',
        # 'https://www.mrisoftware.com',
        # "https://www.binance.com",
        "https://letitbethaicafe.com"
    ]
    fetcher = HTMLFetcher()
    for url in urls:
        s= time.time()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        }
        
        #with cProfile.Profile() as pr:
        fetcher.normal_fetch(url)
        #stats = pstats.Stats(pr)
        #stats.strip_dirs()
        #stats.sort_stats("cumulative").print_stats()
        print(time.time()-s)
    fetcher.close()