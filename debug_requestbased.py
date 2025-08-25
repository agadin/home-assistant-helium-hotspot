#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# example usage:
#   python3 debug_requestbased.py --hotspot 9982
import argparse, json, re, sys, html, requests
from typing import Optional, List, Tuple

def build_corpus(raw: str) -> List[str]:
    v1 = raw
    v2 = html.unescape(raw)
    v3 = (v2.replace(r"\\n", " ")
             .replace(r"\\t", " ")
             .replace("\\/", "/")
             .replace('\\"', '"'))
    return [v1, v2, v3]

NUM  = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
UNIT = r'(?:[KMGTP]?B)'

# HNT line-items
POC_FLOAT_RE = re.compile(r'"label"\s*:\s*"Proof Of Coverage"\s*,\s*"value"\s*:\s*("?)(%s)\1' % NUM, re.S)
DT_FLOAT_RE  = re.compile(r'"label"\s*:\s*"Data Transfer"\s*,\s*"value"\s*:\s*("?)(%s)\1'  % NUM, re.S)

# Display fallback (Tokens Earned card)
TOKENS_DISPLAY_RE = re.compile(
    r'"Tokens Earned".{0,6000}?"children"\s*:\s*\[\s*\[\s*"\$"\s*,\s*"svg"[^]]*?\]\s*,\s*"(%s)"' % NUM,
    re.S,
)

# Data amounts from lineItems
LINEITEMS_RE = re.compile(r'"lineItems"\s*:\s*\[(.*?)\]', re.S)
PAIR_IN_BLOCK_RE = re.compile(r'\{\s*"label"\s*:\s*"(.*?)"\s*,\s*"value"\s*:\s*"(.*?)"\s*\}', re.S)
VALUE_WITH_UNITS_RE = re.compile(r'^\s*%s\s*%s\s*$' % (NUM, UNIT), re.I)

# Avg Daily
META_RE = re.compile(r'property=["\']og:description["\']\s+content=["\']Avg Daily Stats\s*\|\s*([0-9.]+)\s*([KMGT]?B)\s*\|\s*([0-9]+)\s*users["\']', re.I)

def extract_tokens_hnt(corpora: List[str]):
    poc = dt = None
    # sum PoC + DT
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
    # display fallback
    for t in corpora:
        m = TOKENS_DISPLAY_RE.search(t)
        if m:
            try: return poc, dt, round(float(m.group(1)), 3), "display"
            except: pass
    return poc, dt, None, "none"

def extract_data_amounts(corpora: List[str]):
    # prefer lineItems blocks
    for t in corpora:
        for m in LINEITEMS_RE.finditer(t):
            body = m.group(1)
            pairs = dict(PAIR_IN_BLOCK_RE.findall(body))
            co = pairs.get("Carrier Offload")
            hm = pairs.get("Helium Mobile")
            if co and hm and VALUE_WITH_UNITS_RE.match(co) and VALUE_WITH_UNITS_RE.match(hm):
                return co.strip(), hm.strip()
    # fallback: per-object search
    co_m = hm_m = None
    CO_OBJ_RE = re.compile(r'\{\s*"label"\s*:\s*"Carrier Offload"[^}]*"value"\s*:\s*"(.*?)"\s*\}', re.S)
    HM_OBJ_RE = re.compile(r'\{\s*"label"\s*:\s*"Helium Mobile"[^}]*"value"\s*:\s*"(.*?)"\s*\}', re.S)
    for t in corpora:
        co_m = co_m or CO_OBJ_RE.search(t)
        hm_m = hm_m or HM_OBJ_RE.search(t)
    co = co_m.group(1).strip() if co_m else None
    hm = hm_m.group(1).strip() if hm_m else None
    if co and hm and VALUE_WITH_UNITS_RE.match(co) and VALUE_WITH_UNITS_RE.match(hm):
        return co, hm
    return None, None

def extract_avg_daily(corpora: List[str]):
    for t in corpora:
        m = META_RE.search(t)
        if m:
            return f"{m.group(1)} {m.group(2)}", m.group(3)
    return None, None

def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text

def main():
    ap = argparse.ArgumentParser(description="Helium Hotspot scraper (HA-friendly).")
    ap.add_argument("--hotspot", required=True, help="Hotspot number, e.g. 141703")
    args = ap.parse_args()

    url = f"https://world.helium.com/en/network/mobile/hotspot/{args.hotspot}"
    raw_html = fetch_html(url)
    corpora = build_corpus(raw_html)

    poc, dt, hnt_total, hnt_source = extract_tokens_hnt(corpora)
    carrier_offload, helium_mobile = extract_data_amounts(corpora)
    avg_data, avg_users = extract_avg_daily(corpora)

    out = {
        "hotspot": args.hotspot,
        "url": url,
        "proof_of_coverage_30d": poc,
        "data_transfer_30d": dt,
        "tokens_earned_30d_hnt": hnt_total,
        "hnt_source": hnt_source,
        "carrier_offload": carrier_offload,
        "helium_mobile": helium_mobile,
        "avg_daily_data": avg_data,
        "avg_daily_users": avg_users
    }
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Always output valid JSON so HA doesn't error
        print(json.dumps({"error": str(e)}))
        sys.exit(0)
