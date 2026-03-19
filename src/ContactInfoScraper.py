import re
from urllib.parse import urljoin, unquote
import phonenumbers
#from email_scraper import scrape_emails
from src.EmailScraperRobust import scrape_emails
from parsel import Selector
from html2text import HTML2Text
from urllib.parse import unquote
import os
import sys
# Configure html2text
html2text = HTML2Text()
html2text.ignore_links = True  # Keep links if needed
html2text.ignore_images = True

# pages = ('about', 'about-us', 'aboutus', 'contacts', 'contact', 'contactus', 'contact-us', 'customer-service')
pages = (
    'about', 'about-us', 'aboutus', 'contacts', 'contact','contact.html', 'contactus', 'contact-us',  # English
    'acerca', 'acerca-de', 'sobre-nosotros', 'contacto', 'servicio-al-cliente',  # Spanish
    'a-propos', 'qui-sommes-nous', 'contact', 'service-client',  # French
    'uber-uns', 'kontakt', 'kundenservice',  # German
    'chi-siamo', 'contatti', 'contatto',  # Italian
    'sobre', 'sobre-nos', 'contato', 'servico-ao-cliente',  # Portuguese
    'over-ons', 'contact', 'klantenservice',  # Dutch
    'о-нас', 'контакты', 'связаться',  # Russian
    '私たちについて', 'お問い合わせ',  # Japanese
    '关于我们', '联系我们',  # Chinese
    'من-نحن', 'اتصل-بنا',  # Arabic
    'हमारे-बारे-में', 'संपर्क',  # Hindi
    'hakkında', 'iletisim', 'iletisim-bilgileri',  # Turkish
    '우리에 대하여', '연락처',  # Korean
    'om-oss', 'kontakt',  # Swedish
    'om-os', 'kontakt',  # Danish
    'om-oss', 'kontakt',  # Norwegian
    'meista', 'yhteystiedot',  # Finnish
    'σχετικά-με-εμάς', 'επικοινωνία',  # Greek
    'เกี่ยวกับเรา', 'ติดต่อ',  # Thai
    'tentang-kami', 'kontak',  # Indonesian
    've-chung-toi', 'lien-he',  # Vietnamese
    'kapcsolat', 'kapcsolataink', 'kapcsolat-rol', 'kapcsolati-informaciok',  # Hungarian
)

country_codes = ["US", "CR", "IN", "BR", "JP", "FR", "DE"]
social_media_words = (
    'linkedin', 'whatsapp', 'facebook', 'twitter', 'instagram', 'pinterest', 'youtube', 'tiktok')
# These need domain-level matching to avoid false positives (e.g. "rubricx.com" matching "x.com")
social_media_domains = ('x.com', 'wa.me')

black_listed_emails_domains = ['wixpress.com', 'wix.com', 'sentry.io']
business_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]


def _is_social_link(link):
    lower = link.lower()
    if any(word in lower for word in social_media_words):
        return True
    for domain in social_media_domains:
        if f'//{domain}' in lower or f'.{domain}' in lower:
            return True
    return False

def _match_platform(lower_link):
    for platform in social_media_words:
        if platform in lower_link:
            return platform
    for domain in social_media_domains:
        if f'//{domain}' in lower_link or f'.{domain}' in lower_link:
            return domain
    return None

class ContactInfoScraper:
    def process_social_media(self, domain, social_links):
        domain_string = domain.split('.')[0] if domain else ''
        words = ('channel', '.com/@', domain_string)
        http_social = [link for link in social_links if link.startswith(('http', 'www'))]
        social_matches = [link for link in http_social if any(word in link for word in words)]
        if not social_matches:
            social_matches = http_social if http_social else social_links

        # If multiple matches, return them joined by a comma, otherwise return the single link
        return ', '.join(social_matches) if len(social_matches) > 1 else social_matches[0]

    def group_links_by_platform(self, domain, links):
        grouped_links = {}  # Use a single dictionary
        for link in links:
            lower_link = link.lower()
            platform = _match_platform(lower_link)
            if platform:
                if platform == 'x.com':
                    platform = 'twitter'
                elif platform == 'wa.me':
                    platform = 'whatsapp'
                grouped_links.setdefault(platform, []).append(link)

        # Process and update links directly in the same dictionary
        for platform, link_list in grouped_links.items():
            if link_list:  # No need to check len explicitly, just check the list itself
                processed_link = self.process_social_media(domain, link_list)
                grouped_links[platform] = [processed_link]  # Overwrite with processed link

        return {k:','.join(v) for k,v in grouped_links.items()}  # Return the dictionary directly

    def phone_scraper(self, country_codes, text):
        for country_code in country_codes:
            valid_phones = {
                phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.NATIONAL).replace(' ',
                                                                                                          '').replace(
                    '(', '').replace(')', '').replace('-', '')
                for match in phonenumbers.PhoneNumberMatcher(text, country_code)
                if len(phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.NATIONAL)) >= 8
            }
            # Return the first set of valid phone numbers found
            if valid_phones:
                return valid_phones

        return set()

    # def _get_clean_body(self, selector):
    #     """Shared cleaning logic for both text and link extraction"""
    #     # Create a copy of the selector to avoid modifying original
    #     clean_selector = selector
    #     # Remove unwanted elements using XPath
    #     xpaths_to_remove = [
    #         '//script', '//style', '//nav', '//header', '//footer', '//aside',
    #         '//comment()', '//*[@role="navigation"]', '//*[contains(@class, "header")]',
    #         '//*[contains(@class, "footer")]'
    #     ]
    #     for xpath in xpaths_to_remove:
    #         for element in selector.xpath(xpath):
    #             element.drop()
    #
    #     return clean_selector

    def extract_text_from_response(self, html):
        """
        Extract cleaned text content from response using Parsel.
        Returns markdown-formatted text.
        """
        # clean_selector = self._get_clean_body(selector)

        # # Get cleaned HTML from the selector
        # cleaned_html = clean_selector.get()
        return html2text.handle(html)

    def extract_links_from_response(self, selector):
        """
        Extract all page and social media links from response.
        Returns unique absolute URLs.
        """
        # clean_selector = self._get_clean_body(selector)
        clean_selector = selector
        # Extract href attributes explicitly
        hrefs = clean_selector.css(
            'a[href]::attr(href), '
            '[data-href]::attr(data-href), '
            '[data-url]::attr(data-url), '
            '[data-link]::attr(data-link)'
        ).getall()
        # Extract URLs from onclick handlers
        onclick_urls = clean_selector.css('*[onclick]::attr(onclick)').re(r"['\"](https?://[^'\"\\]+)['\"]")

        # Combine and filter links
        all_links = set(
            link.strip()
            for link in hrefs + onclick_urls
            if link and not link.startswith(('javascript:', 'mailto:', 'tel:'))
        )

        # Resolve relative URLs using proper base URL
        base_url = clean_selector.css('base::attr(href)').get() or clean_selector.root.base_url
        resolved_links = {
            urljoin(base_url, link) if not link.startswith(('http', '//')) else link
            for link in all_links
        }

        # Final filtering of non-page links
        return [
            link for link in resolved_links
            if not any(link.endswith(ext) for ext in ('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'))
               and not any(seg in link for seg in ('cdn.', 'static.', 'assets.', 'wp-content/', 'wp-includes/'))
        ]

    def get_contact(self, html, base_url, main_page=False):
        # response = Selector(response_text)
        # hrefs = set(response.css('div a::attr(href)').getall())
        # text_content = ', '.join(response.css('div *::text').getall())
        # hrefs_text = ', '.join(hrefs)
        # links = self.extract_all_links(response)

        selector = Selector(html, base_url=base_url)
        domain = base_url.split('://')[-1].split('/')[0]
        # Extract both text and links from the same cleaned selector
        text = self.extract_text_from_response(html)
        links = self.extract_links_from_response(selector)
        
        emails = scrape_emails(html)

        for email in selector.css('[data-cfemail]::attr(data-cfemail)').getall():
            emails.add(self.decode_cfemail(email))

        # if not emails:
        #     emails = scrape_emails(hrefs_text)
        social_media = [link.strip(',') for link in links if _is_social_link(link)]
        phones = self.phone_scraper(country_codes, text)

        if main_page:
            
            subpages_links = {link for link in links if domain in link}
            return emails, phones, social_media, subpages_links
        else:
            return emails, phones, social_media

    def process_subpage(self, url, response_text):
        emails, phones, social_media = [], [], []

        try:
            # Fetch the URL content using the session
            emails, phones, social_media, _ = self.get_contact(response_text, url)
            print(f"Processed {url}: Emails: {emails}, Phones: {phones}, Social Media: {social_media}")

        except Exception as e:
            print(f"Error processing {url}: {e}")

        return emails, phones, social_media

    def subpages_scraper(self, response, hrefs):
        print('response',response.url)
        subpages_links = {urljoin(response.url, href) for href in hrefs if href.lower().endswith(pages)}
        if not subpages_links:
            subpages_links = {urljoin(response.url, href) for href in hrefs if
                              any(page in href.lower() for page in pages)}
        #print(subpages_links)
        return subpages_links

    @staticmethod
    def decode_cfemail(cfemail):
        """
        Decode Cloudflare-protected email (data-cfemail)
        """
        r = bytes.fromhex(cfemail)
        key = r[0]
        return ''.join(chr(b ^ key) for b in r[1:])


class ContactFilter:
    def emails_filter(self, emails, is_personal_email=False):
        words = black_listed_emails_domains if not is_personal_email else business_domains + black_listed_emails_domains
        return list({self.clean_email(email) for email in emails if not any(word in email for word in words) and email})

    def clean_email(self, email):
        """
        Cleans and normalizes an email address by:
        - Decoding URL and Unicode sequences.
        - Removing invalid symbols from the local part.
        - Ensuring proper formatting.
        """

        if not isinstance(email, str) or "@" not in email:
            return None  # Return None if input is invalid

        # Step 1: URL-decode & Unicode decode
        email = unquote(email)  # Decode %40 → @
        email = email.encode('utf-8').decode('unicode_escape')  # Handle Unicode escape sequences

        # Step 2: Remove unnecessary characters
        email = email.replace('"', '').replace("'", '')  # Remove quotation marks

        # Step 3: Convert to lowercase & strip spaces
        email = email.lower().strip()

        # Step 4: Split local and domain parts
        local_part, domain_part = email.split("@", 1)

        # Step 5: Remove invalid characters in local part (before @)
        allowed_chars = r"[^a-zA-Z0-9._+-]"  # Allowed characters in the local part
        local_part = re.sub(allowed_chars, "", local_part)

        # Step 6: Ensure no consecutive dots or underscores
        local_part = re.sub(r"\.{2,}", ".", local_part)  # Replace multiple dots
        local_part = re.sub(r"_+", "_", local_part)  # Replace multiple underscores

        # Step 7: Ensure it doesn't start or end with . or _
        local_part = local_part.strip("._")

        # Step 8: Ensure domain part is formatted properly
        domain_part = domain_part.lower().strip()

        # Step 9: Reconstruct and return cleaned email
        cleaned_email = f"{local_part}@{domain_part}" if local_part else None
        return cleaned_email

