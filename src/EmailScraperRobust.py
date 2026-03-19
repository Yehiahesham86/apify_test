# requirements (pip): beautifulsoup4 email-validator tldextract
# pip install beautifulsoup4 email-validator tldextract

import regex
import base64
import html
from bs4 import BeautifulSoup
from email_validator import validate_email, EmailNotValidError
import tldextract
import time
import gc
from concurrent.futures import ProcessPoolExecutor


# Ignorance lists as regex fragments
IGNORE_LOCALPARTS_RE = r"(?:user|example|test|noreply)"
IGNORE_DOMAINS_RE = r"(?:domain\.com|example\.com|test\.com|sample\.com|\.js|email\.com)"

# Local part with ignore negative lookahead
LOCAL_PART = (
    rf"(?!{IGNORE_LOCALPARTS_RE}\b)"     # exclude placeholder usernames
    r"[a-z0-9!#$%&'*+\-/=?^_`{|}~]+"     # actual local-part
    r"(?:\.[a-z0-9!#$%&'*+\-/=?^_`{|}~]+)*"
)

# Domain with ignore negative lookahead
DOMAIN_LABEL = r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)"
DOMAIN = (
    rf"(?!{IGNORE_DOMAINS_RE}\b)"        # exclude placeholder domains
    rf"{DOMAIN_LABEL}(?:\.{DOMAIN_LABEL})*"
)

EMAIL_RE = regex.compile(
    rf"""
    {LOCAL_PART}
    @
    {DOMAIN}
    \.
    (?!png\b|jpg\b|jpeg\b|gif\b|bmp\b|svg\b|webp\b)  # exclude image extensions
    [a-z]{{2,}}                                      # main TLD
    (?:\.[a-z]{{2}})?                                # optional country code (e.g. .uk, .de)
    \b
    """,
    regex.IGNORECASE | regex.VERBOSE,
)

# fuzzy obfuscated pattern: user (at) domain (dot) com etc.
FUZZY_OBF =  regex.compile(
    r'([A-Za-z0-9+\._%\-]+)\s*(?:\(|\[|{)?\s*(?:at|@)\s*(?:\)|\]|})?\s*'
    r'([A-Za-z0-9\.\-]+)\s*(?:\(|\[|{)?\s*(?:dot|\.)\s*(?:\)|\]|})?\s*([A-Za-z]{2,})',
     regex.IGNORECASE
)

ATOB_RE =  regex.compile(r'atob\(\s*[\'"]([A-Za-z0-9+/=]+)[\'"]\s*\)',  regex.IGNORECASE)
CHARCODE_RE =  regex.compile(r'String\.fromCharCode\(\s*([0-9,\s]+)\s*\)',  regex.IGNORECASE)

TRAILING_PUNC_RE =  regex.compile(r'^[\s"\']+|[\s\.,;:\)\]\}]+$')

def _clean_candidate(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    s = TRAILING_PUNC_RE.sub('', s)
    s = regex.sub(r'\s+', '', s)  # remove interior whitespace used for obfuscation
    return s

def _decode_atob(text: str) -> str:
    def repl(m):
        try:
            return base64.b64decode(m.group(1).encode('utf-8')).decode('utf-8')
        except Exception:
            return m.group(0)
    return ATOB_RE.sub(repl, text)

def _decode_charcodes(text: str) -> str:
    def repl(m):
        try:
            nums = [int(x.strip()) for x in m.group(1).split(',') if x.strip().isdigit()]
            return ''.join(chr(n) for n in nums)
        except Exception:
            return m.group(0)
    return CHARCODE_RE.sub(repl, text)

def _extract_mailto(soup: BeautifulSoup, results: set):
    for a in soup.select('a[href]'):
        href = a['href']
        if href.lower().startswith('mailto:'):
            addr = href.split(':', 1)[1].split('?')[0]
            addr = _clean_candidate(html.unescape(addr))
            results.add(addr)
def _extract_text_candidates(text: str):
    e=EMAIL_RE.finditer(text,timeout=2,concurrent=True)
    results=set()
    try:
        for m in e:
            candidate = _clean_candidate(m.group(0))
            results.add(candidate)
            if len(results)>=2:
                break
    except TimeoutError:
        pass
    finally:
        gc.collect()
        return list(results)
    
    
    # fuzzy obfuscated like "user (at) domain (dot) com"
    #for m in FUZZY_OBF.finditer(text):
    #    user, dom, tld = m.groups()
    #    candidate = f"{user}@{dom}.{tld}"
    #    candidate = _clean_candidate(candidate)
    #    results.add(candidate)

def validate_and_normalize(candidates):
    good = set()
    for c in candidates:
        try:
            # email_validator normalizes domain (IDN -> punycode if needed) and validates syntax
            v = validate_email(c, check_deliverability=False)
            normalized = v['email']  # this is normalized by library
            # optionally further validate TLD/domain with tldextract
            ext = tldextract.extract(normalized)
            if ext.suffix == '':
                continue
            good.add(normalized)
        except EmailNotValidError:
            continue
        except Exception:
            continue
    return good

def scrape_emails(html_text: str):
    if not html_text:
        return set()
    # 1. simple unescape + decode
    txt = html.unescape(html_text)
    txt = _decode_atob(txt)
    txt = _decode_charcodes(txt)

    soup = BeautifulSoup(txt, 'html.parser')

    candidates = set()

    # 2. extract mailto links
    _extract_mailto(soup, candidates)

    # 3. gather visible text and attributes
    # visible text nodes
    #visible_text = ' '.join(t for t in soup.stripped_strings)
    ## include some attributes that commonly contain emails
    #attr_values = []
    #for tag in soup.find_all():
    #    for key in ('title', 'alt', 'id', 'class'):
    #        val = tag.attrs.get(key)
    #        if not val:
    #            continue
    #        # class and other multi-valued attrs may be lists (AttributeValueList)
    #        if isinstance(val, (list, tuple)):
    #            attr_values.append(' '.join(map(str, val)))
    #        else:
    #            attr_values.append(str(val))
    #attr_text = ' '.join(attr_values)
    #big_text = ' '.join([visible_text, attr_text, txt])

    # 4. run candidate extraction in Parallel Chunks
    #chunks = [big_text[i:i+50000] for i in range(0, len(big_text), 50000)]
    #with ProcessPoolExecutor(max_workers=4) as ex:
    #    results = sum(ex.map(_extract_text_candidates, chunks), [])
    #for r in results:
    #    candidates.add(r)
    for i in _extract_text_candidates(html_text):
        candidates.add(i)
    

    # 5. tidy and validate
    
    cleaned = set(_clean_candidate(c) for c in candidates if c)
    validated = validate_and_normalize(cleaned)
    
    return validated

# quick test
if __name__ == "__main__":
    sample = """
    <a href="mailto:john.doe@example.com">Email</a>
    user (at) example (dot) com
    atob('am9obi5kb2VAZXhhbXBsZS5jb20=')
    <script>var x = String.fromCharCode(106,111,104,110,64,101,120,46,99,111,109);</script>
    """
    print(scrape_emails(sample))
