"""Check the static blog/watch-page discovery graph and video sitemap.

Run with --base origin/main before publishing to check that article content,
source dates, existing video embeds, and inquiry links were preserved.
Uses only the Python standard library; does not make network requests.
"""
import argparse
from datetime import date, datetime
import hashlib
import html
import json
import math
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qs, urljoin, urlsplit
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://intro.wesco.works'
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9',
      'v': 'http://www.google.com/schemas/sitemap-video/1.1',
      'x': 'http://www.w3.org/1999/xhtml'}
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
LOCALE_PREFIXES = {'ko': '', 'en': 'en/', 'zh-CN': 'zh-cn/',
                   'zh-TW': 'zh-tw/', 'ja': 'ja/', 'vi': 'vi/'}
FILM_SLUGS = {'before-after': 'tsp-before-after',
              'singlephase': 'single-phase-installation',
              'threephase': 'three-phase-installation'}
FORM_LOCALES = {'ko': 'ko', 'en': 'en', 'zh-CN': 'cn',
                'zh-TW': 'cn', 'ja': 'en', 'vi': 'vn'}
LEGACY_SLUGS = {'tsp-product', 'tsp-demo', 'wesco-company'}


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.canonicals = []
        self.frames = []
        self.h1_count = 0
        self.styles = []
        self.alternates = {}
        self.lang = None
        self.images = []
        self.ids = []
        self.feed(text)
        self.data = [json.loads(item) for item in LD.findall(text)]

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs)
        if tag == 'iframe':
            self.frames.append(attrs)
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'html':
            self.lang = attrs.get('lang')
        if tag == 'img':
            self.images.append(attrs)
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs.get('href'))
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.styles.append(attrs.get('href'))
        if tag == 'link' and attrs.get('rel') == 'alternate' and attrs.get('hreflang'):
            self.alternates.setdefault(attrs['hreflang'], []).append(attrs.get('href'))


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
    parser.add_argument('--reviewed-content', type=Path,
                        help='Explicit receipt of reviewed article corrections; requires --base. '
                             'Only its exact replacements and matching hashes are allowed.')
    args = parser.parse_args()
    checks = 0

    def check(condition, message):
        nonlocal checks
        assert condition, message
        checks += 1

    reviewed = {}
    if args.reviewed_content:
        check(bool(args.base), '--reviewed-content requires --base')
        receipt = json.loads(text(args.reviewed_content))
        for record in receipt['files']:
            rel = record['path']
            check(re.fullmatch(r'blog/(?:en/)?[a-z0-9-]+/index\.html', rel) is not None,
                  f'Reviewed content must name an existing article: {rel}')
            check(rel not in reviewed, f'Duplicate reviewed path: {rel}')
            check(bool(record['changes']), f'Empty reviewed change list: {rel}')
            reviewed[rel] = record

    learning = json.loads(text(ROOT / 'videos/library-learning.json'))
    lessons = {item['key']: item for item in learning['entries']}
    check(len(learning['entries']) == len(lessons) == 18, 'Expected 18 distinct video lessons')

    sitemap = ET.fromstring(text(ROOT / 'sitemap.xml'))
    entries = {e.findtext('s:loc', namespaces=NS): e for e in sitemap.findall('s:url', NS)}
    check(len(entries) == len(sitemap.findall('s:url', NS)), 'Duplicate sitemap URL')
    for url in entries:
        check(local_target(url).is_file(), f'Missing sitemap target: {url}')

    blog_paths = sorted((ROOT / 'blog').glob('**/index.html'))
    watch_paths = sorted(path for prefix in LOCALE_PREFIXES.values()
                         for path in (ROOT / prefix / 'videos').glob('*/index.html'))
    pages = blog_paths + [ROOT / 'videos/index.html'] + watch_paths
    unique_targets = set()
    preserved_articles = preserved_embeds = preserved_ctas = reviewed_articles = 0
    reviewed_seen = set()
    for path in pages:
        rel = path.relative_to(ROOT).as_posix()
        contents = text(path)
        page = Page(contents)
        url = ORIGIN + '/' + rel.removesuffix('index.html')
        check(page.canonicals == [url], f'Canonical mismatch: {rel}')
        check(page.h1_count == 1, f'Expected one page heading: {rel}')
        check(len(set(page.ids)) == len(page.ids), f'Duplicate HTML id: {rel}')
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
            check('/blog/discovery.css' in page.styles, f'Missing discovery stylesheet: {rel}')
            if not is_hub:
                expected_prefix = '/en/videos/' if rel.startswith('blog/en/') else '/videos/'
                matches = [x for x in page.links if x.get('class') == 'rel discovery-video']
                check(len(matches) == 1 and matches[0]['href'].startswith(expected_prefix), f'Wrong related video language: {rel}')
                check(len(schemas(page, 'Article')) == 1, f'Missing article metadata: {rel}')
        # Pages first published after the base (new posts) have nothing to preserve.
        if args.base and subprocess.run(['git', 'cat-file', '-e', f'{args.base}:{rel}'], cwd=ROOT, stderr=subprocess.DEVNULL).returncode == 0:
            old = subprocess.check_output(['git', 'show', f'{args.base}:{rel}'], cwd=ROOT).decode('utf-8')
            before = Page(old)
            approved_old = old
            if rel in reviewed:
                record = reviewed[rel]
                raw_after = path.read_bytes()
                check(hashlib.sha256(raw_after).hexdigest() == record['afterSha256'],
                      f'Reviewed current file hash differs: {rel}')
                normalized_old = old.replace('\r\n', '\n')
                if 'beforeNormalizedSha256' in record:
                    check(hashlib.sha256(normalized_old.encode('utf-8')).hexdigest() == record['beforeNormalizedSha256'],
                          f'Reviewed baseline content hash differs: {rel}')
                else:
                    old_hashes = {hashlib.sha256(s.encode('utf-8')).hexdigest()
                                  for s in (old, normalized_old, normalized_old.replace('\n', '\r\n'))}
                    check(record['beforeSha256'] in old_hashes, f'Reviewed baseline hash differs: {rel}')
                approved_old = normalized_old
                for change in record['changes']:
                    check(approved_old.count(change['before']) == change['occurrences'],
                          f'Reviewed replacement count differs: {rel}: {change["before"][:45]}')
                    approved_old = approved_old.replace(change['before'], change['after'])
                check(contents == approved_old, f'Unreviewed content change remains: {rel}')
                reviewed_seen.add(rel)
            check(page.frames == before.frames, f'Embedded video changed: {rel}')
            preserved_embeds += len(page.frames)
            if is_blog and not is_hub:
                approved_before = Page(approved_old)
                for kind in ('Article', 'FAQPage'):
                    check(schemas(page, kind) == schemas(approved_before, kind), f'{kind} changed: {rel}')
                for old_article, new_article in zip(schemas(before, 'Article'), schemas(page, 'Article')):
                    for field in ('datePublished', 'dateModified', 'author', 'publisher'):
                        check(old_article.get(field) == new_article.get(field), f'Article {field} changed: {rel}')
                # Related-video recommendations may change; preserve the article's
                # prose, dates, FAQ, and all other recommendations on both sides.
                body = re.search(r'<article\b.*?</article>', contents, re.S).group(0)
                old_body = re.search(r'<article\b.*?</article>', approved_old, re.S).group(0)
                related_video = r'<a class="rel discovery-video"[^>]*>.*?</a>'
                body = re.sub(related_video, '', body, flags=re.S)
                old_body = re.sub(related_video, '', old_body, flags=re.S)
                check(body == old_body, f'Article body changed: {rel}')
                if rel in reviewed: reviewed_articles += 1
                else: preserved_articles += 1
            if path in watch_paths:
                current_data = [dict(item) for item in schemas(page, 'VideoObject')]
                original_data = schemas(before, 'VideoObject')
                # Reviewed chapters may add Clip markup; every pre-existing field
                # stays unchanged. The complete new Clip list is checked below.
                lesson_embeds = {'https://www.youtube.com/embed/'+lesson['videoId']
                                 for lesson in lessons.values() if lesson['transcript']}
                if (len(current_data) == len(original_data) == 1 and 'hasPart' not in original_data[0]
                        and current_data[0].get('embedUrl') in lesson_embeds):
                    current_data[0].pop('hasPart', None)
                check(current_data == original_data, f'Existing video metadata changed: {rel}')
                ctas = lambda p: [x for x in p.links if urlsplit(x.get('href', '')).netloc == 'tsp.wesco.works']
                check(ctas(page) == ctas(before) and len(ctas(page)) == 2, f'Inquiry/catalogue tracking changed: {rel}')
                preserved_ctas += len(ctas(page))

    check(reviewed_seen == set(reviewed), 'Reviewed receipt contains paths absent from the baseline or page set')

    for lang in ('ko', 'en'):
        hub = Page(text(ROOT / ('blog/en/index.html' if lang == 'en' else 'blog/index.html')))
        check(len(schemas(hub, 'CollectionPage')) == 1, f'Missing collection metadata: {lang}')
        prefix = '/blog/en/' if lang == 'en' else '/blog/'
        for slug in ('momentary-outage-compensator-guide', 'ups-vs-outage-compensator',
                     'semiconductor-fab-voltage-sag', 'display-fab-power-quality',
                     'smart-factory-power-quality', 'automotive-line-voltage-sag'):
            check(any(x['href'] == prefix + slug + '/' for x in hub.links), f'Missing topic: {lang}/{slug}')

    video_entries = {u: e for u, e in entries.items() if e.find('v:video', NS) is not None}
    check(len(video_entries) == len(watch_paths) == 24, 'Expected 24 video sitemap/watch pages (18 new + 6 legacy)')
    catalog_file = ROOT / 'videos/library.json'
    check(catalog_file.is_file(), 'Missing public video catalog')
    catalog = json.loads(text(catalog_file))
    catalog = catalog.get('entries', []) if isinstance(catalog, dict) else catalog
    check(isinstance(catalog, list) and len(catalog) == 18, 'Expected 18 current public catalog entries')
    check(len({x['key'] for x in catalog}) == 18, 'Duplicate catalog key')
    check(len({x['videoId'] for x in catalog}) == 18, 'Duplicate catalog video ID')
    check(set(lessons) == {x['key'] for x in catalog}, 'Lesson/catalog keys differ')
    check({(x['locale'], x['film']) for x in catalog} ==
          {(locale, film) for locale in LOCALE_PREFIXES for film in FILM_SLUGS},
          'Catalog must contain all six languages and three films')
    catalog_by_url = {}
    for item in catalog:
        route = '/' + LOCALE_PREFIXES[item['locale']] + 'videos/' + FILM_SLUGS[item['film']] + '/'
        if 'path' in item:
            check(item['path'] == route, f'Unexpected catalog route: {item["key"]}')
        check(re.fullmatch(r'[A-Za-z0-9_-]{11}', item['videoId']) is not None,
              f'Invalid YouTube ID: {item["key"]}')
        catalog_by_url[ORIGIN + route] = item
    library_page = Page(text(ROOT / 'videos/index.html'))
    library_targets = {urljoin(ORIGIN + '/videos/', x.get('href', '')) for x in library_page.links}
    check(set(video_entries).issubset(library_targets), 'Library must link to all 24 current/legacy watch pages')
    check(not library_page.frames, 'Video library must not preload 24 video players')
    source_values = set()
    transcript_count = transcript_cues = chapter_count = concept_count = 0
    for path in watch_paths:
        contents = text(path)
        page = Page(contents)
        data, = schemas(page, 'VideoObject')
        url = page.canonicals[0]
        video = video_entries[url].find('v:video', NS)
        fields = {'title': data['name'], 'description': data['description'],
                  'thumbnail_loc': data['thumbnailUrl'][0], 'player_loc': data['embedUrl'],
                  'publication_date': data['uploadDate']}
        for key, value in fields.items():
            check(video.findtext('v:' + key, namespaces=NS) == value, f'Video sitemap {key} differs from page: {url}')
        iso = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', data['duration'])
        check(iso is not None, f'Invalid ISO duration: {url}')
        seconds = sum(float(n or 0) * factor for n, factor in zip(iso.groups(), (3600, 60, 1)))
        check(int(video.findtext('v:duration', namespaces=NS)) == math.ceil(seconds), f'Video duration mismatch: {url}')
        check(seconds > 0, f'Video duration must be positive: {url}')
        try:
            if len(data['uploadDate']) == 10:
                date.fromisoformat(data['uploadDate'])
            else:
                datetime.fromisoformat(data['uploadDate'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            check(False, f'Invalid upload date: {url}')
        check('contentUrl' not in data, f'Unverified media URL: {url}')
        check(len(page.frames) == 1 and page.frames[0].get('src') == data['embedUrl'], f'Player mismatch: {url}')
        sitemap_alternates = {a.attrib['hreflang']: a.attrib['href']
                              for a in video_entries[url].findall('x:link', NS)}
        expected_langs = set(LOCALE_PREFIXES) | {'x-default'} if url in catalog_by_url else {'ko', 'en'}
        check(set(sitemap_alternates) == expected_langs, f'Missing sitemap language alternates: {url}')
        check(set(page.alternates) == expected_langs, f'Missing HTML language alternates: {url}')
        check(all(len(values) == 1 for values in page.alternates.values()), f'Duplicate hreflang: {url}')
        check({lang: targets[0] for lang, targets in page.alternates.items()} == sitemap_alternates,
              f'HTML/sitemap alternate mismatch: {url}')
        for lang, target in sitemap_alternates.items():
            check(local_target(target).is_file(), f'Missing alternate target: {url} -> {target}')
            reciprocal = Page(text(local_target(target)))
            check(reciprocal.alternates.get(page.lang) == [url], f'Nonreciprocal hreflang: {url} -> {target}')
        blogprefix = '/blog/' if page.lang == 'ko' else '/blog/en/'
        check(sum(x.get('href', '').startswith(blogprefix) for x in page.links) >= 3, f'Missing related guide navigation: {url}')
        if url in catalog_by_url:
            item = catalog_by_url[url]
            lesson = lessons[item['key']]
            check(lesson['videoId'] == item['videoId'] and lesson['locale'] == item['locale'],
                  f'Lesson video/language mismatch: {url}')
            check(html.escape(lesson['summary']) in contents and len(lesson['takeaways']) == 3,
                  f'Missing static learning summary: {url}')
            check(all(html.escape(point) in contents for point in lesson['takeaways']),
                  f'Missing static learning points: {url}')
            check('player' in page.ids, f'Missing time-link player target: {url}')
            chapter_links = [a for a in page.links if a.get('class') == 'chapter-link']
            transcript_links = [a for a in page.links if 'transcript-time' in a.get('class', '').split()]
            if item['film'] == 'before-after':
                check(not lesson['transcript'] and not lesson['chapters'] and not chapter_links
                      and not transcript_links and 'hasPart' not in data,
                      f'Concept film must not invent narration or chapters: {url}')
                concept_count += 1
            else:
                c = learning['copy'][item['locale']]
                check(all(html.escape(c[key]) in contents for key in ('summaryTitle','chaptersTitle','transcriptTitle','transcriptNote','referenceNote')),
                      f'Missing localized learning UI: {url}')
                check(re.fullmatch(r'[a-f0-9]{64}', lesson['captionSha256']) is not None,
                      f'Missing caption provenance hash: {url}')
                check(len(lesson['chapters']) >= 3 and lesson['chapters'][0]['seconds'] == 0,
                      f'Invalid chapter sequence: {url}')
                check(len(chapter_links) == len(lesson['chapters']), f'Chapter count mismatch: {url}')
                expected_clips = []
                previous_start = -1
                for chapter, link in zip(lesson['chapters'], chapter_links):
                    start = chapter['seconds']
                    check(isinstance(start, int) and previous_start < start < seconds,
                          f'Invalid chapter time: {url}')
                    expected_link = item['path'] + '?t=' + str(start) + '#player'
                    check(link['href'] == expected_link and html.escape(chapter['title']) in contents,
                          f'Chapter link/title differs: {url}')
                    expected_clips.append({'@type':'Clip','name':chapter['title'],'startOffset':start,
                                           'url':url+'?t='+str(start)})
                    previous_start = start
                check(data.get('hasPart') == expected_clips, f'Clip/visible chapter mismatch: {url}')
                check(len(transcript_links) == len(lesson['transcript']) >= 10, f'Transcript count mismatch: {url}')
                transcript_html = re.search(r'<details class="video-transcript">.*?</details>', contents, re.S)
                check(transcript_html is not None, f'Missing static transcript: {url}')
                visible_text = html.unescape(re.sub(r'<[^>]+>', '', transcript_html[0]))
                previous_end = 0
                for cue, link in zip(lesson['transcript'], transcript_links):
                    check(previous_end <= cue['start'] < cue['end'] <= seconds + .05,
                          f'Invalid/overlapping caption cue: {url}')
                    check(cue['text'] in visible_text, f'Published caption missing from visible HTML: {url}')
                    check(link['href'] == item['path']+'?t='+str(math.floor(cue['start']))+'#player',
                          f'Transcript timestamp differs from published cue: {url}')
                    previous_end = cue['end']
                transcript_count += 1
                transcript_cues += len(lesson['transcript'])
                chapter_count += len(lesson['chapters'])
            check(page.lang == data['inLanguage'] == item['locale'], f'Video/page/catalog language mismatch: {url}')
            check(data['embedUrl'] == 'https://www.youtube.com/embed/' + item['videoId'], f'Catalog player mismatch: {url}')
            ctas = [urlsplit(x.get('href', '')) for x in page.links if urlsplit(x.get('href', '')).netloc == 'tsp.wesco.works']
            check(len(ctas) == 2 and {c.fragment for c in ctas} == {'contact', 'catalog'}, f'Missing inquiry/catalogue links: {url}')
            check(all(c.path == '/' + FORM_LOCALES[item['locale']] + '/' for c in ctas), f'Wrong form language route: {url}')
            sources = [parse_qs(c.query).get('s', []) for c in ctas]
            check(len(sources[0]) == 1 and sources[0] == sources[1], f'Inconsistent CTA source tracking: {url}')
            source = sources[0][0]
            check(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', source) is not None, f'Invalid CTA source: {url}')
            check(source not in source_values, f'Duplicate per-video CTA source: {url}')
            source_values.add(source)

    check(transcript_count == 12 and concept_count == 6, 'Expected 12 installation transcripts and six concept summaries')

    print(json.dumps({'status': 'passed', 'checks': checks, 'pages': len(pages),
                      'articles': len(blog_paths) - 2, 'video_sitemap_entries': len(video_entries),
                      'current_public_videos': len(catalog), 'tracked_video_sources': len(source_values),
                      'unique_internal_targets': len(unique_targets), 'baseline': args.base,
                      'preserved_article_bodies': preserved_articles, 'preserved_iframes': preserved_embeds,
                      'preserved_inquiry_catalogue_links': preserved_ctas,
                      'reviewed_article_bodies': reviewed_articles,
                      'installation_transcripts': transcript_count, 'transcript_cues': transcript_cues,
                      'verified_chapters': chapter_count, 'concept_summaries': concept_count}, indent=2))


if __name__ == '__main__':
    main()
