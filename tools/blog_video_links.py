"""Shared, offline blog-video recommendations for site and external publishers.

Public interface: get_related_video(site_root, slug, locale) -> {path, label}.
The caller supplies the freshly updated website checkout, not a cached catalog.
Unknown article slugs use the explicit default. Invalid or missing data raises
BlogVideoConfigError and must stop publication rather than fall back silently.
"""
from html.parser import HTMLParser
import json
from pathlib import Path
import re


class BlogVideoConfigError(ValueError):
    """A recommendation cannot be resolved safely from the public site data."""


LOCALES = {'ko': '/videos/', 'en': '/en/videos/'}
FILMS = {'before-after', 'singlephase', 'threephase'}
LEGACY = {'tsp-product', 'tsp-demo', 'wesco-company'}
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
PREFIX = {'ko': '영상으로 확인: ', 'en': 'Watch: '}


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as error:
        raise BlogVideoConfigError(f'Cannot read blog-video data: {path}') from error


def _selection(value):
    if not isinstance(value, str) or ':' not in value:
        raise BlogVideoConfigError(f'Invalid blog-video selection: {value!r}')
    kind, name = value.split(':', 1)
    if not ((kind == 'film' and name in FILMS) or (kind == 'legacy' and name in LEGACY)):
        raise BlogVideoConfigError(f'Unknown blog-video selection: {value!r}')
    return kind, name


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or '<' in value or '>' in value:
        raise BlogVideoConfigError(f'Invalid {field} in blog-video data')
    return ' '.join(value.split())


def _target(root, path, locale):
    if not isinstance(path, str) or not re.fullmatch(re.escape(LOCALES[locale])+r'[a-z0-9-]+/', path):
        raise BlogVideoConfigError(f'Invalid {locale} video path: {path!r}')
    target = root / path.lstrip('/') / 'index.html'
    if not target.is_file():
        raise BlogVideoConfigError(f'Missing video watch page: {path}')
    return path


def get_related_video(site_root, slug, locale):
    """Return the exact relative watch-page URL and localized visible label.

    Latest-series paths/headings are always read from videos/library.json.
    Legacy recommendations use the explicit approved path/title data. Nothing
    is inferred from relatedBlogs, whose many-to-many reading links are not a
    primary-video recommendation. No network access or file writes occur.
    """
    root = Path(site_root).resolve()
    if locale not in LOCALES:
        raise BlogVideoConfigError(f'Unsupported blog locale: {locale!r}')
    if not isinstance(slug, str) or SLUG.fullmatch(slug) is None:
        raise BlogVideoConfigError(f'Invalid article slug: {slug!r}')
    rules = _read_json(root / 'videos/blog-video-links.json')
    catalog = _read_json(root / 'videos/library.json')
    if not isinstance(rules, dict) or rules.get('schemaVersion') != 1:
        raise BlogVideoConfigError('Unsupported blog-video rules schema')
    if not isinstance(rules.get('posts'), dict) or not isinstance(rules.get('legacy'), dict):
        raise BlogVideoConfigError('Missing explicit post/legacy recommendation data')
    _selection(rules.get('default'))
    for post_slug, selection in rules['posts'].items():
        if not isinstance(post_slug, str) or SLUG.fullmatch(post_slug) is None:
            raise BlogVideoConfigError(f'Invalid configured article slug: {post_slug!r}')
        _selection(selection)
    if not isinstance(catalog, list):
        raise BlogVideoConfigError('Video catalog must be a list')
    current = {}
    for item in catalog:
        if not isinstance(item, dict):
            raise BlogVideoConfigError('Invalid video catalog entry')
        if item.get('locale') not in LOCALES:
            continue
        identity = (item['locale'], item.get('film'))
        if identity[1] not in FILMS or identity in current:
            raise BlogVideoConfigError(f'Invalid or duplicate catalog selection: {identity}')
        current[identity] = item
    if set(current) != {(language, film) for language in LOCALES for film in FILMS}:
        raise BlogVideoConfigError('Video catalog is missing a Korean/English current-series entry')
    for (language, _), item in current.items():
        _target(root, item.get('path'), language)
        _text(item.get('heading'), 'current video heading')
    for legacy_name in LEGACY:
        for language in LOCALES:
            try:
                item = rules['legacy'][legacy_name][language]
            except (KeyError, TypeError) as error:
                raise BlogVideoConfigError(f'Missing legacy recommendation: {legacy_name}/{language}') from error
            if not isinstance(item, dict):
                raise BlogVideoConfigError(f'Invalid legacy recommendation: {legacy_name}/{language}')
            _target(root, item.get('path'), language)
            _text(item.get('title'), 'legacy video title')
    kind, name = _selection(rules['posts'].get(slug, rules['default']))
    if kind == 'film':
        item = current[(locale, name)]
        path = _target(root, item.get('path'), locale)
        title = _text(item.get('heading'), 'current video heading')
    else:
        try:
            item = rules['legacy'][name][locale]
        except (KeyError, TypeError) as error:
            raise BlogVideoConfigError(f'Missing legacy recommendation: {name}/{locale}') from error
        path = _target(root, item.get('path'), locale)
        title = _text(item.get('title'), 'legacy video title')
    return {'path': path, 'label': PREFIX[locale]+title}


class _RelatedLinks(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.active = None
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            if {'rel', 'discovery-video'}.issubset(attrs.get('class', '').split()):
                self.active = {'path': attrs.get('href'), 'label': ''}
                self.links.append(self.active)
            else:
                self.active = None

    def handle_data(self, data):
        if self.active is not None:
            self.active['label'] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.active is not None:
            self.active['label'] = ' '.join(self.active['label'].split())
            self.active = None


def validate_related_video_html(site_root, slug, locale, source):
    """Reject absent, duplicate, stale, wrong-language or mislabeled links."""
    expected = get_related_video(site_root, slug, locale)
    actual = _RelatedLinks(source).links
    if actual != [expected]:
        raise BlogVideoConfigError(
            f'Related video mismatch for {locale}/{slug}: expected {expected!r}, found {actual!r}')
    return expected
