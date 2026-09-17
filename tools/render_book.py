"""사업소개서(index.html) 쪽별 렌더링 — 디자인 검수용.
사용: python3 tools/render_book.py [출력폴더] [파일=index.html] [언어=ko]
ko 외 언어는 RENDER_BASE=http://127.0.0.1:8765 (python3 -m http.server) 로 띄워야 사전이 로드된다.
이펙트를 끄고 21쪽을 각각 PNG 로 저장하고, 쪽 안에서 넘치는(overflow) 요소가 있으면 stderr 로 알린다.
"""
import os, sys
from playwright.sync_api import sync_playwright
EXE = os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell")
if not os.path.exists(EXE): EXE = None
out = sys.argv[1] if len(sys.argv) > 1 else "_build/render"
src = sys.argv[2] if len(sys.argv) > 2 else "index.html"
lang = sys.argv[3] if len(sys.argv) > 3 else "ko"
os.makedirs(out, exist_ok=True)
root = os.path.dirname(os.path.abspath(__file__)) + "/.."
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE) if EXE else p.chromium.launch()
    pg = b.new_page(viewport={"width": 1400, "height": 900})
    base = os.environ.get("RENDER_BASE")  # 예: http://127.0.0.1:8765 — file:// 에선 fetch(i18n) 가 막혀 ko 만 나온다
    pg.goto(f"{base}/{src}?lang={lang}" if base else f"file://{os.path.abspath(os.path.join(root, src))}?lang={lang}")
    pg.wait_for_timeout(2000)
    if pg.query_selector("#fx"):
        pg.click("#fx"); pg.wait_for_timeout(1000)
    els = pg.query_selector_all(".page")
    for i, el in enumerate(els, 1):
        el.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
        el.screenshot(path=f"{out}/p{i:02d}.png")
        ov = el.evaluate(r"""e=>{const r=e.getBoundingClientRect();const bad=[];
          e.querySelectorAll('*').forEach(c=>{const s=getComputedStyle(c);if(s.position==='fixed'||s.display==='none')return;
          const q=c.getBoundingClientRect();if(q.width===0||q.height===0)return;
          const band=e.querySelector('.band');const bt=band?band.getBoundingClientRect().top:Infinity;
          const inBand=band&&(c===band||band.contains(c));
          if(!inBand&&q.bottom>bt+1&&q.top<bt)bad.push('BAND '+c.tagName.toLowerCase()+(c.className&&typeof c.className==='string'?'.'+c.className.split(' ')[0]:'')+' +'+Math.round(q.bottom-bt)+'px');
          if(q.right>r.right+1||q.bottom>r.bottom+1)bad.push(c.tagName.toLowerCase()+(c.className&&typeof c.className==='string'?'.'+c.className.split(' ')[0]:'')+' +'+Math.round(Math.max(q.right-r.right,q.bottom-r.bottom))+'px')});
          return bad.filter(b=>!/^BAND section\b/.test(b)).slice(0,6)}""")
        if ov: print(f"p{i:02d} OVERFLOW: {ov}", file=sys.stderr)
    print(f"{len(els)} pages -> {out}")
    b.close()
