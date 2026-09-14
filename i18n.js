/**
 * WESCO 사업소개 i18n
 * - Loads i18n/<lang>.json
 * - Replaces text in elements with [data-i18n="key"]
 * - For elements with [data-i18n-attr="content"|"placeholder"|"alt"|...],
 *   updates that attribute instead of textContent
 * - Persists choice in localStorage
 * - Updates <html lang> + <meta name="description">
 */
(function () {
  const SUPPORTED = ['ko', 'en', 'cn', 'jp', 'vn'];
  const DEFAULT_LANG = 'ko';
  const STORAGE_KEY = 'wesco-intro-lang';
  const dicts = {}; // cache: { ko: {...}, en: {...}, ... }

  function getInitialLang() {
    // URL parameter has highest priority (?lang=en)
    const urlLang = new URLSearchParams(location.search).get('lang');
    if (urlLang && SUPPORTED.includes(urlLang)) return urlLang;
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && SUPPORTED.includes(saved)) return saved;
    const browser = (navigator.language || 'ko').slice(0, 2).toLowerCase();
    if (browser === 'zh') return 'cn';
    if (browser === 'ja') return 'jp';
    if (browser === 'vi') return 'vn';
    if (SUPPORTED.includes(browser)) return browser;
    return DEFAULT_LANG;
  }

  async function loadDict(lang) {
    if (dicts[lang]) return dicts[lang];
    try {
      const res = await fetch(`i18n/${lang}.json?v=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      dicts[lang] = data;
      return data;
    } catch (e) {
      console.warn(`[i18n] Failed to load ${lang}.json:`, e);
      return null;
    }
  }

  // Void elements that cannot have text content
  const VOID_TAGS = new Set(['br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'param', 'source', 'track', 'wbr']);

  function applyDict(dict, lang) {
    if (!dict) return;
    // Element text + attribute replacement
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const val = dict[key];
      if (val == null) return; // missing translation: keep current text
      const attrName = el.getAttribute('data-i18n-attr');
      if (attrName) {
        el.setAttribute(attrName, val);
      } else if (el.hasAttribute('data-i18n-html')) {
        // 표지 h1 처럼 <br>/<em> 이 섞인 문장 — 사전 값을 HTML 로 그대로 넣는다 (사전은 우리 파일뿐이므로 안전)
        el.innerHTML = val;
      } else if (VOID_TAGS.has(el.tagName.toLowerCase())) {
        // Skip void elements (br, hr, etc.) — they cannot hold text
        return;
      } else {
        // Preserve child nodes that aren't text? Most data-i18n elements are leaf-like.
        // If element has child elements, only replace the first/last text node.
        if (el.children.length === 0) {
          el.textContent = val;
        } else {
          // Replace ONLY the first non-empty direct text-node child.
          // Other text nodes (tails after inline children) are handled by their own data-i18n keys.
          let replaced = false;
          for (const node of Array.from(el.childNodes)) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
              node.textContent = val;
              replaced = true;
              break;
            }
          }
          if (!replaced) {
            // Fallback: prepend text node
            el.insertBefore(document.createTextNode(val), el.firstChild);
          }
        }
      }
    });

    // Update <html lang>
    document.documentElement.lang = lang === 'cn' ? 'zh' : (lang === 'jp' ? 'ja' : (lang === 'vn' ? 'vi' : lang));

    // Toggle UI state
    document.querySelectorAll('[data-lang-btn]').forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-lang-btn') === lang);
    });

    // 스크립트가 동적으로 만드는 문구(이펙트 버튼 등)를 위해 사전을 공개하고 알린다
    window.__dict = dict;
    document.dispatchEvent(new CustomEvent('wesco:i18n', { detail: { lang } }));
  }

  async function setLang(lang) {
    if (!SUPPORTED.includes(lang)) return;
    const dict = await loadDict(lang);
    if (!dict) return;
    applyDict(dict, lang);
    localStorage.setItem(STORAGE_KEY, lang);
  }

  // Expose for buttons / debugging
  window.WescoI18n = { setLang, getInitialLang, SUPPORTED };

  // Init on DOM ready
  function init() {
    // Wire up language toggle buttons
    document.querySelectorAll('[data-lang-btn]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const lang = btn.getAttribute('data-lang-btn');
        setLang(lang);
      });
    });

    // Apply initial language (ko is the source; only fetch if different)
    const initial = getInitialLang();
    if (initial !== 'ko') {
      setLang(initial);
    } else {
      // Mark KO active
      document.querySelectorAll('[data-lang-btn="ko"]').forEach((b) => b.classList.add('active'));
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
