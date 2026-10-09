"""Check the static blog/watch-page discovery graph and video sitemap.

Run with --base origin/main before publishing to check that article content,
source dates, existing video embeds, and inquiry links were preserved.
Uses only the Python standard library; does not make network requests.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://intro.wesco.works'
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9',
      'v': 'http://www.google.com/schemas/sitemap-video/1.1',
      'x': 'http://www.w3.org/1999/xhtml'}
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.canonicals = []
        self.frames = []
        self.h1_count = 0
        self.styles = []
        self.feed(text)
        self.data = [json.loads(item) for item in LD.findall(text)]

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.links.append(attrs)
        if tag == 'iframe':
            self.frames.append(attrs)
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs.get('href'))
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.styles.append(attrs.get('href'))


def text(path):
    return path.read_text(encoding='utf-8')


def schemas(page, kind):
    return [item for item in page.data if item.get('@type') == kind]


def local_target(url):
    path = urlsplit(url).path
    target = ROOT / path.lstrip('/')
    return target / 'index.html' if path.endswith('/') else target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='Optional Git ref for preservation checks')
    args = parser.parse_args()
    checks = 0

    def check(condition, message):
        nonlocal checks
        assert condition, message
        checks += 1

    sitemap = ET.fromstring(text(ROOT / 'sitemap.xml'))
    entries = {e.findtext('s:loc', namespaces=NS): e for e in sitemap.findall('s:url', NS)}
    check(len(entries) == len(sitemap.findall('s:url', NS)), 'Duplicate sitemap URL')
    for url in entries:
        check(local_target(url).is_file(), f'Missing sitemap target: {url}')

    blog_paths = sorted((ROOT / 'blog').glob('**/index.html'))
    watch_paths = sorted((ROOT / 'videos').glob('*/index.html')) + sorted((ROOT / 'en/videos').glob('*/index.html'))
    pages = blog_paths + [ROOT / 'videos/index.html'] + watch_paths
    unique_targets = set()
    preserved_articles = preserved_embeds = preserved_ctas = 0
    for path in pages:
        rel = path.relative_to(ROOT).as_posix()
        contents = text(path)
        page = Page(contents)
        url = ORIGIN + '/' + rel.removesuffix('index.html')
        check(page.canonicals == [url], f'Canonical mismatch: {rel}')
        check(page.h1_count == 1, f'Expected one page heading: {rel}')
        check(url in entries, f'Page absent from sitemap: {url}')
        for link in page.links:
            href = link.get('href', '')
            resolved = urljoin(url, href)
            if urlsplit(resolved).netloc == 'intro.wesco.works':
                check(local_target(resolved).is_file(), f'Broken link from {rel}: {href}')
                unique_targets.add(resolved)
        for style in page.styles:
            if style.startswith('/'):
                check(local_target(ORIGIN + style).is_file(), f'Missing stylesheet: {style}')
        is_blog = rel.startswith('blog/')
        is_hub = rel in ('blog/index.html', 'blog/en/index.html', 'videos/index.html')
        if is_blog:
            check(not schemas(page, 'VideoObject'), f'Unverified supplementary-video metadata: {rel}')
            check(any(x.get('href') == '/videos/' for x in page.links), f'No video navigation: {rel}')
            if not is_hub:
                expected_prefix = '/en/videos/' if rel.startswith('blog/en/') else '/videos/'
                matches = [x for x in page.links if x.get('class') == 'rel discovery-video']
                check(len(matches) == 1 and matches[0]['href'].startswith(expected_prefix), f'Wrong related video language: {rel}')
                check(len(schemas(page, 'Article')) == 1, f'Missing article metadata: {rel}')
        if args.base:
            old = subprocess.check_output(['git', 'show', f'{args.base}:{rel}'], cwd=ROOT).decode('utf-8')
            before = Page(old)
            check(page.frames == before.frames, f'Embedded video changed: {rel}')
            preserved_embeds += len(page.frames)
            if is_blog and not is_hub:
                for kind in ('Article', 'FAQPage'):
                    check(schemas(page, kind) == schemas(before, kind), f'{kind} changed: {rel}')
                # Ignore only the newly inserted related-video anchor. All article
                # prose, source dates, and existing recommendations stay intact.
                body = re.search(r'<article\b.*?</article>', contents, re.S).group(0)
                body = re.sub(r'<a class="rel discovery-video"[^>]*>.*?</a>', '', body)
                old_body = re.search(r'<article\b.*?</article>', old, re.S).group(0)
                check(body == old_body, f'Article body changed: {rel}')
                preserved_articles += 1
            if path in watch_paths:
                check(schemas(page, 'VideoObject') == schemas(before, 'VideoObject'), f'Existing video metadata changed: {rel}')
                ctas = lambda p: [x for x in p.links if urlsplit(x.get('href', '')).netloc == 'tsp.wesco.works']
                check(ctas(page) == ctas(before) and len(ctas(page)) == 2, f'Inquiry/catalogue tracking changed: {rel}')
                preserved_ctas += len(ctas(page))

    for lang in ('ko', 'en'):
        hub = Page(text(ROOT / ('blog/en/index.html' if lang == 'en' else 'blog/index.html')))
        check(len(schemas(hub, 'CollectionPage')) == 1, f'Missing collection metadata: {lang}')
        prefix = '/blog/en/' if lang == 'en' else '/blog/'
        for slug in ('momentary-outage-compensator-guide', 'ups-vs-outage-compensator',
                     'semiconductor-fab-voltage-sag', 'display-fab-power-quality',
                     'smart-factory-power-quality', 'automotive-line-voltage-sag'):
            check(any(x['href'] == prefix + slug + '/' for x in hub.links), f'Missing topic: {lang}/{slug}')

    video_entries = {u: e for u, e in entries.items() if e.find('v:video', NS) is not None}
    check(len(video_entries) == len(watch_paths) == 6, 'Video sitemap/watch-page count mismatch')
    for path in watch_paths:
        page = Page(text(path))
        data, = schemas(page, 'VideoObject')
        url = page.canonicals[0]
        video = video_entries[url].find('v:video', NS)
        fields = {'title': data['name'], 'description': data['description'],
                  'thumbnail_loc': data['thumbnailUrl'][0], 'player_loc': data['embedUrl'],
                  'publication_date': data['uploadDate']}
        for key, value in fields.items():
            check(video.findtext('v:' + key, namespaces=NS) == value, f'Video sitemap {key} differs from page: {url}')
        iso = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', data['duration'])
        seconds = sum(int(n or 0) * factor for n, factor in zip(iso.groups(), (3600, 60, 1)))
        check(int(video.findtext('v:duration', namespaces=NS)) == seconds, f'Video duration mismatch: {url}')
        check('contentUrl' not in data, f'Unverified media URL: {url}')
        check(page.frames[0]['src'] == data['embedUrl'], f'Player mismatch: {url}')
        check({a.attrib['hreflang'] for a in video_entries[url].findall('x:link', NS)} == {'ko', 'en'}, f'Missing language alternates: {url}')
        blogprefix = '/blog/en/' if '/en/videos/' in url else '/blog/'
        check(sum(x.get('href', '').startswith(blogprefix) for x in page.links) >= 3, f'Missing related guide navigation: {url}')

    print(json.dumps({'status': 'passed', 'checks': checks, 'pages': len(pages),
                      'articles': len(blog_paths) - 2, 'video_sitemap_entries': len(video_entries),
                      'unique_internal_targets': len(unique_targets), 'baseline': args.base,
                      'preserved_article_bodies': preserved_articles, 'preserved_iframes': preserved_embeds,
                      'preserved_inquiry_catalogue_links': preserved_ctas}, indent=2))


if __name__ == '__main__':
    main()
