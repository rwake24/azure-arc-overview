#!/usr/bin/env python3
"""Validate all external links in MDX content pages.

Usage:
  python scripts/check-links.py           # Check all links
  python scripts/check-links.py --strict  # Exit 1 on broken links (for CI)
"""

import os
import re
import sys
import urllib.request
import urllib.error
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

PAGES_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'content', 'pages')

# URLs that are examples/placeholders, not real links
SKIP_PATTERNS = [
    'localhost',
    'proxy.contoso',
    'my-keyvault.vault.azure.net',
    'example.com',
]


def extract_links(pages_dir):
    """Extract all external URLs from MDX files."""
    links = {}
    for fname in sorted(os.listdir(pages_dir)):
        if not fname.endswith('.mdx'):
            continue
        page = fname.replace('.mdx', '')
        with open(os.path.join(pages_dir, fname), 'r') as f:
            content = f.read()
        for url in re.findall(r'https?://[^\s\)>"\']+', content):
            url = url.rstrip('.,;:')
            if any(p in url for p in SKIP_PATTERNS):
                continue
            if url not in links:
                links[url] = []
            links[url].append(page)
    return links


def check_url(url, timeout=15):
    """Check a single URL, return (url, status_code, error_msg)."""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method='HEAD', headers={
        'User-Agent': 'Mozilla/5.0 (link-checker)'
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return (url, resp.getcode(), None)
    except urllib.error.HTTPError as e:
        # HEAD might be rejected, try GET for 405/403
        if e.code in (405, 403):
            try:
                req2 = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (link-checker)'
                })
                resp = urllib.request.urlopen(req2, timeout=timeout, context=ctx)
                return (url, resp.getcode(), None)
            except urllib.error.HTTPError as e2:
                return (url, e2.code, str(e2))
        return (url, e.code, str(e))
    except Exception as e:
        return (url, 0, str(e))


def main():
    strict = '--strict' in sys.argv
    pages_dir = os.path.abspath(PAGES_DIR)

    print(f"Scanning {pages_dir} for external links...\n")
    links = extract_links(pages_dir)
    print(f"Found {len(links)} unique external links.\n")

    broken = []
    ok = []
    warnings = []

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(check_url, url): (url, pages) for url, pages in links.items()}
        for future in as_completed(futures):
            url, pages = futures[future]
            url, code, error = future.result()
            pages_str = ', '.join(pages)

            if code == 0:
                broken.append((url, f"ERR: {error}", pages_str))
                print(f"  ❌ ERR  [{pages_str}] {url}")
                print(f"         {error}")
            elif code == 404 or code == 410:
                broken.append((url, str(code), pages_str))
                print(f"  ❌ {code} [{pages_str}] {url}")
            elif code >= 400:
                warnings.append((url, str(code), pages_str))
                print(f"  ⚠️  {code} [{pages_str}] {url}")
            else:
                ok.append((url, str(code), pages_str))
                print(f"  ✅ {code} [{pages_str}] {url}")

    print(f"\n{'=' * 60}")
    print(f"✅ OK: {len(ok)}  |  ⚠️ Warnings: {len(warnings)}  |  ❌ Broken: {len(broken)}")

    if broken:
        print(f"\nBROKEN LINKS ({len(broken)}):")
        for url, code, pages in broken:
            print(f"  {code} [{pages}] {url}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for url, code, pages in warnings:
            print(f"  {code} [{pages}] {url}")

    if strict and broken:
        sys.exit(1)


if __name__ == '__main__':
    main()
