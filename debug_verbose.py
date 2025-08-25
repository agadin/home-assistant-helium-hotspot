#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import html
import json
import re
import sys
from typing import Optional, Tuple, List

# example usage:
#   python3 debug_verbose.py --file example.html
#   python3 debug_verbose.py --url https://world.helium.com/en/network/mobile/hotspot/9982
# ==================== Normalization ====================

def build_corpus(raw: str) -> List[str]:
    """Return multiple normalized variants so regexes hit regardless of escaping."""
    v1 = raw
    v2 = html.unescape(raw)
    v3 = (
        v2.replace(r"\\n", " ")
          .replace(r"\\t", " ")
          .replace("\\/", "/")
          .replace('\\"', '"')
    )
    return [v1, v2, v3]

# ==================== Regex Patterns ====================

# Floats (quoted or bare), allow scientific notation
NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
# Data units
UNIT = r'(?:[KMGTP]?B)'

# ---- HNT (PoC & DT as floats) ----
POC_FLOAT_RE = re.compile(r'"label"\s*:\s*"Proof Of Coverage"\s*,\s*"value"\s*:\s*("?)(%s)\1' % NUM, re.S)
DT_FLOAT_RE  = re.compile(r'"label"\s*:\s*"Data Transfer"\s*,\s*"value"\s*:\s*("?)(%s)\1'  % NUM, re.S)

# Tokens display fallback in the “Tokens Earned” card
TOKENS_DISPLAY_RE = re.compile(
    r'"Tokens Earned".{0,6000}?"children"\s*:\s*\[\s*\[\s*"\$"\s*,\s*"svg"[^]]*?\]\s*,\s*"(%s)"' % NUM,
    re.S,
)

# ---- Data amounts: label + value with units (must be in the same object) ----
# Scan all lineItems arrays (simple non-greedy to next ])
LINEITEMS_RE = re.compile(r'"lineItems"\s*:\s*\[(.*?)\]', re.S)
# Within a lineItems body, capture all label/value string pairs
PAIR_IN_BLOCK_RE = re.compile(
    r'\{\s*"label"\s*:\s*"(.*?)"\s*,\s*"value"\s*:\s*"(.*?)"\s*\}', re.S
)
# Accept values like "65.52 MB", "400.86 kB" (case-insensitive on unit)
VALUE_WITH_UNITS_RE = re.compile(r'^\s*%s\s*%s\s*$' % (NUM, UNIT), re.I)

# Avg daily meta (optional)
META_RE = re.compile(
    r'property=["\']og:description["\']\s+content=["\']Avg Daily Stats\s*\|\s*([0-9.]+)\s*([KMGT]?B)\s*\|\s*([0-9]+)\s*users["\']',
    re.I
)

# ==================== Parsers ====================

def extract_tokens_hnt(corpora: List[str]) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    """
    Return (poc, dt, total, source) for HNT (30D).
    Strategy:
      1) Sum PoC + Data Transfer floats from any corpus.
      2) Fallback to displayed number in Tokens card.
    """
    poc = dt = None

    # Try PoC/DT float line-items
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
            total = round(poc + dt, 3)
            return poc, dt, total, "sum"

    # Fallback: tokens display in card
    for t in corpora:
        m = TOKENS_DISPLAY_RE.search(t)
        if m:
            try:
                return poc, dt, round(float(m.group(1)), 3), "display"
            except:
                pass

    return poc, dt, None, "none"

def extract_data_amounts(corpora: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Return (carrier_offload, helium_mobile) strictly from lineItems arrays containing
    { "label":"Carrier Offload","value":"##.## MB" } and
    { "label":"Helium Mobile","value":"##.## MB" }.
    Requires unit-suffixed values; ignores numeric-only values to avoid HNT confusion.
    """
    for t in corpora:
        for m in LINEITEMS_RE.finditer(t):
            body = m.group(1)
            pairs = dict(PAIR_IN_BLOCK_RE.findall(body))
            co = pairs.get("Carrier Offload")
            hm = pairs.get("Helium Mobile")
            # Only accept if both look like "##.## <UNIT>"
            if co and hm and VALUE_WITH_UNITS_RE.match(co) and VALUE_WITH_UNITS_RE.match(hm):
                return co.strip(), hm.strip()

    # Fallback: tighter object-local search (label and value inside one object)
    CO_OBJ_RE = re.compile(
        r'\{\s*"label"\s*:\s*"Carrier Offload"[^}]*"value"\s*:\s*"(.*?)"\s*\}', re.S
    )
    HM_OBJ_RE = re.compile(
        r'\{\s*"label"\s*:\s*"Helium Mobile"[^}]*"value"\s*:\s*"(.*?)"\s*\}', re.S
    )
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

# ==================== Loaders ====================

def load_file_html(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

async def load_url_html(url: str, max_wait_ms: int = 8000) -> str:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await pw.chromium.launch_persistent_context("", headless=True)  # ephemeral profile helps with streaming
        try:
            page = await ctx.new_page()
        except Exception:
            # fallback to non-persistent context if needed
            await ctx.close()
            ctx = await pw.chromium.launch_persistent_context(None, headless=True)
            page = await ctx.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Nudge lazy content a bit
        for _ in range(4):
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(200)

        # brief poll for streamed chunks
        elapsed = 0
        step = 400
        html_text = await page.content()
        while elapsed <= max_wait_ms:
            html_text = await page.content()
            if any(s in html_text for s in ('"lineItems"', '"Proof Of Coverage"', '"Data Transfer"', '"Helium Mobile"', '"Carrier Offload"')):
                break
            await page.wait_for_timeout(step)
            elapsed += step

        await ctx.close()
        await browser.close()
        return html_text

# ==================== Main ====================

async def main():
    ap = argparse.ArgumentParser(description="Scrape Helium hotspot: HNT (30D) + data amounts (Carrier Offload, Helium Mobile).")
    ap.add_argument("--file", help="Path to rendered HTML")
    ap.add_argument("--url", help="Hotspot URL (fetch via Playwright)")
    ap.add_argument("--max-wait-ms", type=int, default=8000, help="Max poll time for URL mode")
    args = ap.parse_args()

    if not args.file and not args.url:
        sys.exit("Provide --file or --url")

    if args.file:
        raw = load_file_html(args.file)
    else:
        raw = await load_url_html(args.url, max_wait_ms=args.max_wait_ms)

    corpora = build_corpus(raw)

    # HNT (PoC + DT)
    poc, dt, hnt_total, hnt_source = extract_tokens_hnt(corpora)

    # Data amounts (strictly value-with-units)
    carrier_offload, helium_mobile = extract_data_amounts(corpora)

    # Avg daily (optional)
    avg_data, avg_users = extract_avg_daily(corpora)

    out = {
        "proof_of_coverage_30d": poc,
        "data_transfer_30d": dt,
        "tokens_earned_30d_hnt": hnt_total,
        "hnt_source": hnt_source,
        "carrier_offload": carrier_offload,   # e.g., "400.86 kB"
        "helium_mobile": helium_mobile,       # e.g., "65.52 MB"
        "avg_daily_data": avg_data,
        "avg_daily_users": avg_users
    }
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
