// All video links remain in the static HTML. Only the language view is filtered.
(() => {
  const buttons = [...document.querySelectorAll('[data-language-filter]')];
  const sections = [...document.querySelectorAll('[data-video-language]')];
  const status = document.getElementById('filter-status');
  const valid = new Set(['all', ...sections.map(s => s.dataset.videoLanguage)]);
  const apply = key => {
    const selected = valid.has(key) ? key : 'ko';
    sections.forEach(s => { s.hidden = selected !== 'all' && s.dataset.videoLanguage !== selected; });
    buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.languageFilter === selected)));
    const button = buttons.find(b => b.dataset.languageFilter === selected);
    status.textContent = `${button.textContent.trim()} · ${selected === 'all' ? 18 : 3}편`;
  };
  buttons.forEach(button => button.addEventListener('click', () => {
    const key = button.dataset.languageFilter;
    history.replaceState(null, '', `#${key}`);
    apply(key);
  }));
  window.addEventListener('hashchange', () => apply(location.hash.slice(1)));
  apply(location.hash.slice(1));
})();
