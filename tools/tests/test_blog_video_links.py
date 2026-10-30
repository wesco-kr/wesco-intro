"""Regression checks for the shared website/external-publisher recommendation contract."""
import html
import json
from pathlib import Path
import sys
import shutil
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from blog_video_links import BlogVideoConfigError, get_related_video, validate_related_video_html
import build_video_library


# Migration acceptance cases, independent of the new rules file. Existing real
# demonstration/company links are deliberately not all replaced by new films.
CURRENT = {
    'tsp-before-after': ['outage-vs-voltage-sag', 'factory-outage-damage',
                         'semiconductor-fab-voltage-sag', 'display-fab-power-quality'],
    'single-phase-installation': ['control-power-protection'],
    'three-phase-installation': ['selecting-sag-protector-capacity', 'smart-factory-power-quality',
                                'automotive-line-voltage-sag', 'voltage-sag-monitoring']}
OLD = {
    'tsp-product': ['10-year-maintenance-free', 'battery-free-voltage-sag',
                    'ev-battery-plant-power-quality', 'faq-voltage-sag-basics',
                    'itic-curve-guide', 'lv-scope-explained', 'momentary-outage-compensator-guide',
                    'semi-f47-explained', 'summer-lightning-season', 'supercapacitor-tech-explained',
                    'ups-vs-outage-compensator'],
    'tsp-demo': ['momentary-power-outage', 'voltage-sag-cost-structure', 'why-sags-come-from-outside'],
    'wesco-company': ['global-track-record']}


def anchor(item):
    return f'<a class="rel discovery-video" href="{html.escape(item["path"])}">{html.escape(item["label"])}</a>'


class ExistingRecommendations(unittest.TestCase):
    def test_current_18_and_legacy_29_recommendations_and_visible_labels(self):
        counts = {'current': 0, 'legacy': 0}
        for group, recommendations in [('current', CURRENT), ('legacy', OLD)]:
            for video_slug, post_slugs in recommendations.items():
                for slug in post_slugs:
                    for locale in ('ko', 'en'):
                        if slug == 'battery-free-voltage-sag' and locale == 'en':
                            continue  # This historical post exists only in Korean.
                        prefix = '/en' if locale == 'en' else ''
                        item = get_related_video(ROOT, slug, locale)
                        with self.subTest(slug=slug, locale=locale):
                            self.assertEqual(item['path'], prefix+'/videos/'+video_slug+'/')
                            post = ROOT/('blog/en' if locale == 'en' else 'blog')/slug/'index.html'
                            validate_related_video_html(ROOT, slug, locale, post.read_text(encoding='utf-8'))
                        counts[group] += 1
        self.assertEqual(counts, {'current': 18, 'legacy': 29})

    def test_explicit_choice_handles_ambiguous_reading_links_and_planned_article(self):
        self.assertEqual(get_related_video(ROOT, 'selecting-sag-protector-capacity', 'ko')['path'],
                         '/videos/three-phase-installation/')
        self.assertEqual(get_related_video(ROOT, 'plc-momentary-outage', 'en')['path'],
                         '/en/videos/single-phase-installation/')
        self.assertEqual(get_related_video(ROOT, 'voltage-sag-monitoring', 'en')['path'],
                         '/en/videos/three-phase-installation/')


class PublisherContract(unittest.TestCase):
    def setUp(self):
        self.temp_parent = (ROOT/'_build/blog-video-link-tests').resolve()
        self.temp_parent.mkdir(parents=True, exist_ok=True)
        self.root = self.temp_parent/('case-'+uuid.uuid4().hex)
        self.root.mkdir()
        self.rules = json.loads((ROOT/'videos/blog-video-links.json').read_text(encoding='utf-8'))
        self.catalog = json.loads((ROOT/'videos/library.json').read_text(encoding='utf-8'))
        (self.root/'videos').mkdir()
        self.save()
        paths = [item['path'] for item in self.catalog]
        paths += [item['path'] for variants in self.rules['legacy'].values() for item in variants.values()]
        for path in paths:
            page = self.root/path.lstrip('/')/'index.html'
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text('<!doctype html><title>Existing public watch page</title>', encoding='utf-8')

    def tearDown(self):
        # Delete only this fixture beneath the explicitly verified build root.
        self.assertTrue(self.root.resolve().is_relative_to(self.temp_parent))
        self.assertTrue(self.root.name.startswith('case-'))
        shutil.rmtree(self.root)

    def save(self):
        (self.root/'videos/blog-video-links.json').write_text(json.dumps(self.rules, ensure_ascii=False), encoding='utf-8')
        (self.root/'videos/library.json').write_text(json.dumps(self.catalog, ensure_ascii=False), encoding='utf-8')

    def test_new_article_uses_only_explicit_default(self):
        item = get_related_video(self.root, 'new-technical-article', 'en')
        self.assertEqual(item['path'], '/en/videos/tsp-product/')
        validate_related_video_html(self.root, 'new-technical-article', 'en', anchor(item))
        self.rules.pop('default')
        self.save()
        with self.assertRaises(BlogVideoConfigError):
            get_related_video(self.root, 'new-technical-article', 'en')

    def test_catalog_change_is_read_without_cached_paths_or_headings(self):
        selected = next(item for item in self.catalog if item['key'] == 'ko-singlephase')
        selected.update(path='/videos/updated-single-phase/', heading='업데이트된 단상 설치 안내')
        p = self.root/'videos/updated-single-phase/index.html'
        p.parent.mkdir(); p.write_text('<title>Updated page</title>', encoding='utf-8')
        self.save()
        self.assertEqual(get_related_video(self.root, 'control-power-protection', 'ko'),
                         {'path':'/videos/updated-single-phase/', 'label':'영상으로 확인: 업데이트된 단상 설치 안내'})

    def test_missing_catalog_fails_closed_even_for_new_legacy_default(self):
        (self.root/'videos/library.json').unlink()
        for slug in ('control-power-protection', 'new-article'):
            with self.subTest(slug=slug), self.assertRaises(BlogVideoConfigError):
                get_related_video(self.root, slug, 'ko')

    def test_missing_current_language_and_duplicate_catalog_fail_closed(self):
        self.catalog = [item for item in self.catalog if item['key'] != 'en-singlephase']
        self.save()
        with self.assertRaises(BlogVideoConfigError):
            get_related_video(self.root, 'control-power-protection', 'en')
        self.catalog = json.loads((ROOT/'videos/library.json').read_text(encoding='utf-8'))
        self.catalog.append(dict(self.catalog[0])); self.save()
        with self.assertRaises(BlogVideoConfigError):
            get_related_video(self.root, 'new-article', 'ko')

    def test_invalid_mapping_missing_page_and_unsupported_locale_fail_closed(self):
        self.rules['posts']['control-power-protection'] = 'film:typo'
        self.save()
        with self.assertRaises(BlogVideoConfigError):
            get_related_video(self.root, 'control-power-protection', 'ko')
        self.rules['posts']['control-power-protection'] = 'film:singlephase'; self.save()
        (self.root/'videos/single-phase-installation/index.html').unlink()
        with self.assertRaises(BlogVideoConfigError):
            get_related_video(self.root, 'control-power-protection', 'ko')
        with self.assertRaises(BlogVideoConfigError):
            get_related_video(self.root, 'control-power-protection', 'ja')

    def test_old_same_language_link_and_wrong_label_are_rejected(self):
        new = get_related_video(self.root, 'control-power-protection', 'ko')
        old = get_related_video(self.root, 'new-article', 'ko')
        with self.assertRaises(BlogVideoConfigError):
            validate_related_video_html(self.root, 'control-power-protection', 'ko', anchor(old))
        with self.assertRaises(BlogVideoConfigError):
            validate_related_video_html(self.root, 'control-power-protection', 'ko', anchor(dict(new, label=old['label'])))

    def test_missing_and_duplicate_recommendation_elements_are_rejected(self):
        item = get_related_video(self.root, 'control-power-protection', 'en')
        for source in ('<p>No related video</p>', anchor(item)+anchor(item)):
            with self.subTest(source=source), self.assertRaises(BlogVideoConfigError):
                validate_related_video_html(self.root, 'control-power-protection', 'en', source)

    def test_shared_generator_repairs_link_once_without_rewriting_article(self):
        post = self.root/'blog/control-power-protection/index.html'
        post.parent.mkdir(parents=True)
        old = get_related_video(self.root, 'new-article', 'ko')
        new = get_related_video(self.root, 'control-power-protection', 'ko')
        before = '<article><p>Original article and date.</p>'+anchor(old)+'</article>'
        post.write_text(before, encoding='utf-8')
        with patch.object(build_video_library, 'ROOT', self.root):
            self.assertEqual(build_video_library.update_blog_links(), ['blog/control-power-protection/index.html'])
            self.assertEqual(post.read_text(encoding='utf-8'), before.replace(anchor(old), anchor(new)))
            self.assertEqual(build_video_library.update_blog_links(), [])
            post.write_text('<article>No recommendation element.</article>', encoding='utf-8')
            with self.assertRaises(BlogVideoConfigError):
                build_video_library.update_blog_links()


if __name__ == '__main__':
    unittest.main()
