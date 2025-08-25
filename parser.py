import html
import re
from typing import Dict, List, Optional, Tuple

NUM  = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
UNIT = r'(?:[KMGTP]?B)'

# HNT (PoC, Data Transfer as floats)
POC_FLOAT_RE = re.compile(r'"label"\s*:\s*"Proof Of Coverage"\s*,\s*"value"\s*:\s*("?)(%s)\1' % NUM, re.S)
DT_FLOAT_RE  = re.compile(r'"label"\s*:\s*"Data Transfer"\s*,\s*"value"\s*:\s*("?)(%s)\1'  % NUM, re.S)

# Display fallback in “Tokens Earned” card
TOKENS_DISPLAY_RE = re.compile(
    r'"Tokens Earned".{0,6000}?"children"\s*:\s*\[\s*\[\s*"\$"\s*,\s*"svg"[^]]*?\]\s*,\s*"(%s)"' % NUM,
    re.S,
)

# Data amounts in lineItems
LINEITEMS_RE = re.compile(r'"lineItems"\s*:\s*\[(.*?)\]', re.S)
PAIR_IN_BLOCK_RE = re.compile(r'\{\s*"label"\s*:\s*"(.*?)"\s*,\s*"value"\s*:\s*"(.*?)"\s*\}', re.S)
VALUE_WITH_UNITS_RE = re.compile(r'^\s*%s\s*%s\s*$' % (NUM, UNIT), re.I)

# Avg daily meta
META_RE = re.compile(
    r'property=["\']og:description["\']\s+content=["\']Avg Daily Stats\s*\|\s*([0-9.]+)\s*([KMGT]?B)\s*\|\s*([0-9]+)\s*users["\']',
    re.I
)

# Hotspot friendly name (e.g., "Mammoth Clay Narwhal")
HOTSPOT_NAME_RE = re.compile(
    r'<div[^>]*class="[^"]*text-3xl[^"]*"[^>]*>(.*?)</div>', re.S
)

# Hotspot name block (large title)
HOTSPOT_NAME_DIV_RE = re.compile(
    r'<div[^>]*class="[^"]*text-3xl[^"]*"[^>]*>(.*?)</div>',
    re.S
)

# After the name div, the next short text-y div often contains "City, State[, Country]"
# We grab a window right after the name and look for a simple comma-separated location.
LOCATION_IN_WINDOW_RE = re.compile(
    r'<div[^>]*>\s*([A-Za-z0-9\s\.\'\-\u00C0-\u024F]+,\s*[A-Za-z0-9\s\.\'\-\u00C0-\u024F]+(?:,\s*[A-Za-z0-9\s\.\'\-\u00C0-\u024F]+)?)\s*</div>',
    re.S
)

# Fallback: any short-ish div anywhere that looks like "City, State[, Country]"
LOCATION_GLOBAL_RE = re.compile(
    r'<div[^>]*class="[^"]*"[^>]*>\s*([A-Za-z0-9\s\.\'\-\u00C0-\u024F]+,\s*[A-Za-z0-9\s\.\'\-\u00C0-\u024F]+(?:,\s*[A-Za-z0-9\s\.\'\-\u00C0-\u024F]+)?)\s*</div>',
    re.S
)

TAG_STRIP_RE = re.compile(r'<[^>]+>')


def _strip_tags(s: str) -> str:
    return TAG_STRIP_RE.sub('', s or '').strip()


def extract_hotspot_name(corpora: List[str]) -> Optional[str]:
    for t in corpora:
        m = HOTSPOT_NAME_DIV_RE.search(t)
        if m:
            return _strip_tags(html.unescape(m.group(1)))
    return None


def extract_hotspot_location(corpora: List[str]) -> Optional[str]:
    # Try: find the name block and scan the next ~800 chars for a comma-separated location
    for t in corpora:
        m = HOTSPOT_NAME_DIV_RE.search(t)
        if not m:
            continue
        start = m.end()
        window = t[start:start+800]
        m_loc = LOCATION_IN_WINDOW_RE.search(window)
        if m_loc:
            loc = _strip_tags(html.unescape(m_loc.group(1)))
            # sanity checks: contains comma(s) and not too long
            if ',' in loc and 3 <= len(loc) <= 120:
                return ' '.join(loc.split())

    # Fallback: search globally for a short comma-separated location-looking div
    for t in corpora:
        for m in LOCATION_GLOBAL_RE.finditer(t):
            loc = _strip_tags(html.unescape(m.group(1)))
            if ',' in loc and 3 <= len(loc) <= 120:
                return ' '.join(loc.split())

    return None

def build_corpus(raw: str) -> List[str]:
    v1 = raw
    v2 = html.unescape(raw)
    v3 = (
        v2.replace(r"\\n", " ")
          .replace(r"\\t", " ")
          .replace("\\/", "/")
          .replace('\\"', '"')
    )
    return [v1, v2, v3]

def extract_tokens_hnt(corpora: List[str]) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    poc = dt = None
    for t in corpora:
        if poc is None:
            m = POC_FLOAT_RE.search(t)
            if m:
                try: poc = float(m.group(2))
                except: poc = None
        if dt is None:
            m = DT_FLOAT_RE.search(t)
            if m:
                try: dt = float(m.group(2))
                except: dt = None
        if poc is not None and dt is not None:
            return poc, dt, round(poc + dt, 3), "sum"
    for t in corpora:
        m = TOKENS_DISPLAY_RE.search(t)
        if m:
            try: return poc, dt, round(float(m.group(1)), 3), "display"
            except: pass
    return poc, dt, None, "none"

def extract_data_amounts(corpora: List[str]) -> Tuple[Optional[str], Optional[str]]:
    for t in corpora:
        for m in LINEITEMS_RE.finditer(t):
            body = m.group(1)
            pairs = dict(PAIR_IN_BLOCK_RE.findall(body))
            co = pairs.get("Carrier Offload")
            hm = pairs.get("Helium Mobile")
            if co and hm and VALUE_WITH_UNITS_RE.match(co) and VALUE_WITH_UNITS_RE.match(hm):
                return co.strip(), hm.strip()
    # fallback per-object
    CO_OBJ_RE = re.compile(r'\{\s*"label"\s*:\s*"Carrier Offload"[^}]*"value"\s*:\s*"(.*?)"\s*\}', re.S)
    HM_OBJ_RE = re.compile(r'\{\s*"label"\s*:\s*"Helium Mobile"[^}]*"value"\s*:\s*"(.*?)"\s*\}', re.S)
    for t in corpora:
        co_m = CO_OBJ_RE.search(t)
        hm_m = HM_OBJ_RE.search(t)
        co = co_m.group(1).strip() if co_m else None
        hm = hm_m.group(1).strip() if hm_m else None
        if co and hm and VALUE_WITH_UNITS_RE.match(co) and VALUE_WITH_UNITS_RE.match(hm):
            return co, hm
    return None, None

def extract_avg_daily(corpora: List[str]) -> Tuple[Optional[str], Optional[str]]:
    for t in corpora:
        m = META_RE.search(t)
        if m:
            return f"{m.group(1)} {m.group(2)}", m.group(3)
    return None, None

def parse_hotspot_html(raw_html: str) -> Dict[str, Optional[str]]:
    corpora = build_corpus(raw_html)
    poc, dt, total, source = extract_tokens_hnt(corpora)
    co, hm = extract_data_amounts(corpora)
    avg_data, avg_users = extract_avg_daily(corpora)

    # NEW:
    name = extract_hotspot_name(corpora)
    location = extract_hotspot_location(corpora)

    return {
        "proof_of_coverage_30d": poc,
        "data_transfer_30d": dt,
        "tokens_earned_30d_hnt": total,
        "hnt_source": source,
        "carrier_offload": co,
        "helium_mobile": hm,
        "avg_daily_data": avg_data,
        "avg_daily_users": avg_users,
        "hotspot_name": name,          # NEW
        "hotspot_location": location,  # NEW
    }
