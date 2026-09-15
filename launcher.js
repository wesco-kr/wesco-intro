/* WESCO 사이트 런처 — 어느 wesco.works 사이트에서든 한 줄로 붙인다.
 *
 *   <script src="https://intro.wesco.works/launcher.js?v=1" defer data-mount="[data-wesco-launcher]"></script>
 *
 * 목록은 같은 origin 의 sites.json 한 파일이 정본이다(라벨 5개국어 포함). 사이트가 늘면 그 파일만 고친다.
 * 언어는 <html lang> 에서 읽는다(zh→cn, ja→jp, vi→vn). lang 이 바뀌면 다시 그린다.
 * data-mount 로 지정한 자리에 버튼을 넣고, 자리가 없으면 오른쪽 아래에 떠 있는 버튼을 만든다.
 * 스타일은 전부 wl- 접두어로 이 파일 안에 있다 — 붙이는 사이트의 CSS 를 건드리지 않는다.
 */
(function () {
  'use strict';
  var me = document.currentScript;
  var base = me && me.src ? me.src.replace(/[^\/]*(\?.*)?$/, '') : '/';
  var mountSel = me && me.getAttribute('data-mount');
  var data = null, btn, drawer, scrim, list;

  var CSS = '.wl-btn{all:unset;box-sizing:border-box;cursor:pointer;display:inline-flex;align-items:center;gap:7px;height:34px;padding:0 12px;border:1px solid #E7E2DA;border-radius:2px;background:#FDFCF9;color:#44403C;font:600 13px/1 "Malgun Gothic","Noto Sans KR",Arial,sans-serif;white-space:nowrap}'
    + '.wl-btn svg{width:13px;height:13px;color:#E1431B;flex:none}.wl-btn:hover{border-color:#E1431B}'
    + '.wl-btn.wl-float{position:fixed;right:16px;bottom:16px;z-index:9990;box-shadow:0 8px 24px rgba(41,37,36,.18)}'
    + '.wl-scrim{position:fixed;inset:0;z-index:9998;background:rgba(28,25,23,.42)}'
    + '.wl-drawer{position:fixed;top:0;right:0;bottom:0;z-index:9999;width:360px;max-width:92vw;background:#FDFCF9;border-left:1px solid #E7E2DA;box-shadow:-16px 0 40px rgba(41,37,36,.18);display:flex;flex-direction:column;transform:translateX(100%);transition:transform .28s;font-family:"Malgun Gothic","Noto Sans KR",Arial,sans-serif;color:#44403C;text-align:left}'
    + '.wl-drawer.wl-open{transform:none}'
    + '.wl-hd{display:flex;align-items:center;justify-content:space-between;padding:18px 20px 16px;border-bottom:1px solid #E7E2DA;font-size:13px;font-weight:700;letter-spacing:.06em}'
    + '.wl-hd button{all:unset;cursor:pointer;font-size:24px;line-height:1;color:#8A847D;padding:0 4px}'
    + '.wl-list{overflow-y:auto;padding:8px 0 24px}'
    + '.wl-g{padding:14px 20px 6px;font:700 10.5px/1 Arial,sans-serif;letter-spacing:.14em;color:#E1431B}'
    + '.wl-list a{display:block;padding:11px 20px;text-decoration:none;color:#44403C;border-left:2px solid transparent}'
    + '.wl-list a:hover,.wl-list a.wl-cur{background:#F6F1EA;border-left-color:#E1431B}'
    + '.wl-list a b{display:block;font-size:14px;font-weight:700}.wl-list a small{display:block;font-size:11.5px;color:#8A847D;margin-top:2px;line-height:1.5}';

  function lang() { var l = (document.documentElement.lang || 'ko').slice(0, 2); return { zh: 'cn', ja: 'jp', vi: 'vn' }[l] || l; }
  function T(o) { var l = lang(); return (o && (o[l] || o.ko)) || ''; }
  function href(h) { var l = lang(); return h.replace('{lang}', l).replace('{tsp}', l === 'jp' ? 'en' : l); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function build() {
    if (!data) return;
    var here = location.origin + location.pathname;
    var label = T(data.label) || 'WESCO';
    btn.querySelector('span').textContent = label;
    drawer.querySelector('.wl-hd b').textContent = label;
    list.innerHTML = data.groups.map(function (g) {
      return '<div class="wl-g">' + esc(T(g.title)) + '</div>' + g.items.map(function (it) {
        var h = href(it.href), same = h.indexOf(location.origin) === 0;
        var cur = h.replace(/#.*$/, '') === here || h === location.origin + '/' ? ' class="wl-cur"' : '';
        return '<a href="' + esc(h) + '"' + cur + (same ? '' : ' target="_blank" rel="noopener"') + '><b>' + esc(T(it.title)) + '</b><small>' + esc(T(it.desc)) + '</small></a>';
      }).join('');
    }).join('');
  }
  function open() { drawer.hidden = false; scrim.hidden = false; requestAnimationFrame(function () { drawer.classList.add('wl-open'); }); btn.setAttribute('aria-expanded', 'true'); }
  function close() { drawer.classList.remove('wl-open'); btn.setAttribute('aria-expanded', 'false'); setTimeout(function () { drawer.hidden = true; scrim.hidden = true; }, 280); }

  function mount() {
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    btn = document.createElement('button'); btn.type = 'button'; btn.className = 'wl-btn'; btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'wl-drawer');
    btn.innerHTML = '<svg viewBox="0 0 14 14" aria-hidden="true"><g fill="currentColor"><circle cx="2" cy="2" r="1.6"/><circle cx="7" cy="2" r="1.6"/><circle cx="12" cy="2" r="1.6"/><circle cx="2" cy="7" r="1.6"/><circle cx="7" cy="7" r="1.6"/><circle cx="12" cy="7" r="1.6"/><circle cx="2" cy="12" r="1.6"/><circle cx="7" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/></g></svg><span>WESCO</span>';
    var m = mountSel && document.querySelector(mountSel);
    if (m) m.appendChild(btn); else { btn.classList.add('wl-float'); document.body.appendChild(btn); }
    scrim = document.createElement('div'); scrim.className = 'wl-scrim'; scrim.hidden = true;
    drawer = document.createElement('aside'); drawer.className = 'wl-drawer'; drawer.id = 'wl-drawer'; drawer.hidden = true; drawer.setAttribute('aria-label', 'WESCO sites');
    drawer.innerHTML = '<div class="wl-hd"><b>WESCO</b><button type="button" aria-label="close">×</button></div><div class="wl-list"></div>';
    list = drawer.querySelector('.wl-list');
    document.body.appendChild(scrim); document.body.appendChild(drawer);
    btn.onclick = function () { drawer.hidden ? open() : close(); }; scrim.onclick = close; drawer.querySelector('.wl-hd button').onclick = close;
    addEventListener('keydown', function (e) { if (e.key === 'Escape' && !drawer.hidden) close(); });
    new MutationObserver(build).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  }

  var ready = fetch(base + 'sites.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  function start() { mount(); ready.then(function (d) { data = d; build(); }).catch(function () { btn.hidden = true; }); }
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);

  window.WescoLauncher = { ready: ready, open: function () { open(); }, close: function () { close(); }, lang: lang, t: T, href: href };
})();
