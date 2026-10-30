// All video links remain in the static HTML. Only the language view is filtered.
(() => {
  const buttons = [...document.querySelectorAll('[data-language-filter]')];
  const sections = [...document.querySelectorAll('[data-video-language]')];
  const status = document.getElementById('filter-status');
  const valid = new Set(['all', ...sections.map(s => s.dataset.videoLanguage)]);
  const copyNode = document.getElementById('hub-copy');
  let copy = {};
  try { copy = copyNode ? JSON.parse(copyNode.textContent) : {}; } catch (error) { copy = {}; }
  const stored = () => {
    try {
      const value = localStorage.getItem('wesco-intro-lang');
      return /^(ko|en|cn|jp|vn)$/.test(value) ? {ko:'ko', en:'en', cn:'zh-CN', jp:'ja', vn:'vi'}[value] : 'ko';
    } catch (error) { return 'ko'; }
  };
  const lines = (node, values) => node.replaceChildren(...values.map(text => {
    const span = document.createElement('span');
    span.className = 'hub-line';
    span.textContent = text;
    return span;
  }));
  // 상단 안내 문구·메뉴 라벨·html lang 을 선택한 언어로 바꾼다(textContent 만 사용). 전체 보기는 저장 언어를 따른다.
  const localize = lang => {
    const c = Object.prototype.hasOwnProperty.call(copy, lang) ? copy[lang] : null;
    if (!c) return null;
    document.documentElement.lang = lang;
    lines(document.querySelector('.library-hero h1'), c.title);
    lines(document.querySelector('.library-hero .lead'), c.lead);
    document.querySelectorAll('.library-meta span').forEach((node, n) => { node.textContent = c.meta[n]; });
    document.querySelectorAll('.topnav a').forEach((node, n) => { node.textContent = c.nav[n]; });
    return c;
  };
  const apply = key => {
    const selected = valid.has(key) ? key : 'ko';
    sections.forEach(s => { s.hidden = selected !== 'all' && s.dataset.videoLanguage !== selected; });
    buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.languageFilter === selected)));
    const button = buttons.find(b => b.dataset.languageFilter === selected);
    const c = localize(selected === 'all' ? stored() : selected);
    const n = selected === 'all' ? 18 : 3;
    status.textContent = `${button.textContent.trim()} · ${c ? c.unit.replace('{n}', n) : n}`;
  };
  buttons.forEach(button => button.addEventListener('click', () => {
    const key = button.dataset.languageFilter;
    history.replaceState(null, '', `#${key}`);
    apply(key);
  }));
  window.addEventListener('hashchange', () => apply(location.hash.slice(1) || stored()));
  // 해시가 없고 첫 화면에서 고른 언어가 있으면 그 언어 필터로 연다
  const first = location.hash.slice(1) || stored();
  if (!location.hash && first !== 'ko') history.replaceState(null, '', `#${first}`);
  apply(first);
})();
