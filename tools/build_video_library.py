"""Render the public multilingual video library from verified release metadata.

Run with Python's standard library. This does not publish videos, make network
requests, or change existing legacy watch pages. Keep local file paths and
production/approval records out of the public data files.
"""
import html
import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from blog_video_links import BlogVideoConfigError, get_related_video

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://intro.wesco.works'
ENTRIES = json.loads((ROOT/'videos/library.json').read_text(encoding='utf-8'))
COPY = json.loads((ROOT/'videos/library-copy.json').read_text(encoding='utf-8'))
LEARNING = json.loads((ROOT/'videos/library-learning.json').read_text(encoding='utf-8'))
LESSONS = {item['key']: item for item in LEARNING['entries']}
ORDER = ['ko','en','zh-CN','zh-TW','ja','vi']
HOME_LANG = {'ko':'ko','en':'en','zh-CN':'cn','zh-TW':'cn','ja':'jp','vi':'vn'}
FILMS = ['before-after','singlephase','threephase']
e = html.escape

def write(path, value):
    dest = ROOT/path.lstrip('/')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(value, encoding='utf-8')

def ld(data):
    return '<script type="application/ld+json">'+json.dumps(data, ensure_ascii=False).replace('</','<\\/')+'</script>'

def duration(seconds):
    s = math.ceil(seconds)
    return f'{s//60}:{s%60:02d}'

NAV = {  # 상단 메뉴 정본(회사소개서 · 기술 자료 · 영상 · 문의하기). 블로그 topbar()·영상 페이지 헤더와 같은 구조
    'ko':('회사소개서','기술 자료','영상','문의하기'),
    'en':('Company Profile','Technical Guides','Videos','Contact us'),
    'zh-CN':('公司介绍','技术资料（英文）','视频','联系我们'),
    'zh-TW':('公司介紹','技術資料（英文）','影片','聯絡我們'),
    'ja':('会社案内','技術資料（英語）','動画','お問い合わせ'),
    'vi':('Hồ sơ công ty','Tài liệu kỹ thuật (tiếng Anh)','Video','Liên hệ')}
CONTACT_LANG = {'ko':'ko','en':'en','zh-CN':'cn','zh-TW':'cn','ja':'en','vi':'vn'}
# 영문 페이지는 첫 화면에서 고른 언어(localStorage)가 있으면 그 언어의 회사소개서로 돌아간다
HOME_SCRIPT = ("<script>try{var l=localStorage.getItem('wesco-intro-lang'),a=document.querySelector('.topnav a[data-home]');"
               "if(a&&/^(en|cn|jp|vn)$/.test(l))a.href='/?lang='+l}catch(e){}</script>")

def header(locale, source='videos'):
    home, blogtext, videos, contact = NAV[locale]
    blog = '/blog/' if locale == 'ko' else '/blog/en/'
    homelink = f'<a data-home href="/?lang={HOME_LANG[locale]}">{e(home)}</a>'
    contacturl = f"https://tsp.wesco.works/{CONTACT_LANG[locale]}/?s=nav_{source}#contact"
    script = HOME_SCRIPT if locale == 'en' else ''
    return (f'<header class="topbar"><div class="wrap"><a class="brand" href="/?lang={HOME_LANG[locale]}" aria-label="WESCO"><img src="/images/wesco_wordmark.png" width="119" height="22" alt="WESCO"></a>'
            f'<nav class="topnav">{homelink}<a href="{blog}">{blogtext}</a><a href="/videos/#{locale}">{e(videos)}</a>'
            f'<a class="nav-cta" href="{contacturl}">{e(contact)}</a></nav></div>{script}</header>')

def head(locale, title, description, path, thumbnail=None, alternates=''):
    ogimage = ORIGIN+thumbnail if thumbnail else ORIGIN+'/images/og-image.jpg'
    return f'''<!doctype html><html lang="{locale}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{ORIGIN+path}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{ORIGIN+path}"><meta property="og:image" content="{ogimage}"><meta property="og:type" content="{'video.other' if thumbnail else 'website'}"><meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="/videos/watch.css"><link rel="stylesheet" href="/videos/library.css">{alternates}'''

def card(item):
    c = COPY[item['locale']]
    num = FILMS.index(item['film'])+1
    return f'''<article class="video-card"><a class="thumb" href="{item['path']}" tabindex="-1" aria-hidden="true"><img src="{item['thumbnail']}" alt="" width="1280" height="720" loading="lazy"><span class="duration">{duration(item['durationSeconds'])}</span></a><div class="card-body"><span class="card-kicker">WESCO TSP® / 0{num}</span><h3><a href="{item['path']}">{e(item['heading'])}</a></h3><p>{e(item['description'])}</p><a class="watch-link" href="{item['path']}">{e(c['watch'])} <span aria-hidden="true">→</span></a></div></article>'''

def footer(locale):
    c = COPY[locale]
    return f'''<footer class="library-footer"><span>© WESCO · TSP®</span><span><a href="https://www.wesco.co.kr">{e(c['officialWebsite'])}</a> · <a href="mailto:wesco@wesco.co.kr">wesco@wesco.co.kr</a></span></footer>'''

def video_schema(item):
    data = {'@context':'https://schema.org','@type':'VideoObject','@id':ORIGIN+item['path']+'#video',
            'name':item['title'],'description':item['description'],
            'thumbnailUrl':[ORIGIN+item['thumbnail']], 'uploadDate':item['publishedAt'],
            'duration':f"PT{item['durationSeconds']:g}S",'embedUrl':item['embedUrl'],'inLanguage':item['locale'],
            'publisher':{'@type':'Organization','@id':ORIGIN+'/#org','name':'WESCO'},
            'mainEntityOfPage':{'@type':'WebPage','@id':ORIGIN+item['path']}}
    chapters = LESSONS[item['key']]['chapters']
    if chapters:
        data['hasPart'] = [{'@type':'Clip', 'name':chapter['title'],
                            'startOffset':chapter['seconds'],
                            'endOffset':chapters[index+1]['seconds'] if index+1 < len(chapters) else math.floor(item['durationSeconds']),
                            'url':ORIGIN+item['path']+'?t='+str(chapter['seconds'])}
                           for index, chapter in enumerate(chapters)]
    return data

def learning_content(item):
    lesson = LESSONS[item['key']]
    assert lesson['videoId'] == item['videoId'] and lesson['locale'] == item['locale']
    c = LEARNING['copy'][item['locale']]
    out = f'''<section class="video-learning" aria-labelledby="learning-title"><h2 id="learning-title">{e(c['summaryTitle'])}</h2><p>{e(lesson['summary'])}</p><ul class="learning-points">'''
    out += ''.join(f'<li>{e(point)}</li>' for point in lesson['takeaways'])+'</ul></section>'
    if not lesson['transcript']:
        assert item['film'] == 'before-after' and not lesson['chapters']
        return out
    out += f'''<p class="note installation-reference">{e(c['referenceNote'])}</p><nav class="video-chapters" aria-labelledby="chapters-title"><h2 id="chapters-title">{e(c['chaptersTitle'])}</h2><p class="time-hint">{e(c['timeHint'])}</p><ol>'''
    for chapter in lesson['chapters']:
        seconds = chapter['seconds']
        out += f'<li><a class="chapter-link" href="{item["path"]}?t={seconds}#player"><span class="timecode">{seconds//60:02d}:{seconds%60:02d}</span><span>{e(chapter["title"])}</span></a></li>'
    out += f'''</ol></nav><details class="video-transcript"><summary><h2>{e(c['transcriptTitle'])}</h2></summary><p class="transcript-note">{e(c['transcriptNote'])}</p><ol>'''
    for cue in lesson['transcript']:
        seconds = math.floor(cue['start'])
        out += f'<li class="transcript-cue" data-start="{cue["start"]}" data-end="{cue["end"]}"><a class="transcript-time timecode" href="{item["path"]}?t={seconds}#player">{seconds//60:02d}:{seconds%60:02d}</a><p>{e(cue["text"])}</p></li>'
    return out+'</ol></details>'

def guide_title(path):
    source = (ROOT/path.lstrip('/')/'index.html').read_text(encoding='utf-8')
    text = re.search(r'<h1[^>]*>(.*?)</h1>',source,re.S).group(1)
    return html.unescape(re.sub('<[^>]+>','',text))

def render_watch(item):
    locale = item['locale']; c = COPY[locale]
    siblings = [i for i in ENTRIES if i['film']==item['film']]
    alternates = ''.join(f'<link rel="alternate" hreflang="{i["locale"]}" href="{ORIGIN+i["path"]}">' for i in siblings)
    default = next(i for i in siblings if i['locale']=='en')
    alternates += f'<link rel="alternate" hreflang="x-default" href="{ORIGIN+default["path"]}">'
    switch = ''.join(f'<a href="{i["path"]}" lang="{i["locale"]}" hreflang="{i["locale"]}"'+(' aria-current="page"' if i['locale']==locale else '')+f'>{e(COPY[i["locale"]]["name"])}</a>' for i in siblings)
    others = [i for i in ENTRIES if i['locale']==locale and i['film']!=item['film']]
    guides = ''.join(f'<li><a href="{p}">{e(guide_title(p))}</a></li>' for p in item['relatedBlogs'])
    body = head(locale,item['title'],item['description'],item['path'],item['thumbnail'],alternates)+ld(video_schema(item))
    body += f'''<script src="/videos/watch.js" defer></script></head><body class="series-watch">{header(locale, item['key'])}<main id="main">
<p class="eyebrow">WESCO TSP® / VIDEO</p><h1 class="watch-title">{e(item['heading'])}</h1>
<div class="player" id="player"><iframe src="{item['embedUrl']}" title="{e(item['title'])}" data-duration="{item['durationSeconds']}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>
<div class="watch-meta"><span>{e(COPY[locale]['name'])} · {duration(item['durationSeconds'])} · {e(c['published'])} <time datetime="{item['publishedDate']}">{item['publishedDate']}</time></span><a href="{item['url']}">{e(c['watchYouTube'])} ↗</a></div>
<nav class="language-switch" aria-label="{e(c['chooseLanguage'])}">{switch}</nav>
<p class="watch-description">{e(item['description'])}</p><p class="note">{e(c['illustrationNote'])}</p>
{learning_content(item)}
<section class="video-cta" aria-label="{e(c['contact'])}"><p>{e(c['contactIntro'])}</p><div class="video-cta-actions"><a class="video-cta-primary" href="{e(item['contactUrl'])}">{e(c['contact'])}</a><a class="video-cta-secondary" href="{e(item['catalogUrl'])}">{e(c['catalog'])}</a></div>'''
    if c['contactLanguageNote']: body += f'<p class="note">{e(c["contactLanguageNote"])}</p>'
    body += f'''</section><div class="related-grid"><nav class="related" aria-label="{e(c['relatedVideos'])}"><h2>{e(c['relatedVideos'])}</h2><ul>'''
    body += ''.join(f'<li><a href="{i["path"]}">{e(i["heading"])}</a></li>' for i in others)
    body += f'''</ul></nav><nav class="related" aria-label="{e(c['relatedGuides'])}"><h2>{e(c['relatedGuides'])}</h2><p class="guide-lang">{e(c['relatedGuidesLanguageNote'])}</p><ul>{guides}</ul></nav></div>{footer(locale)}</main></body></html>\n'''
    write(item['path']+'index.html',body)

def legacy_cards():
    rows=[]
    for prefix,lang in [('','한국어'),('/en','English')]:
        for slug in ['tsp-product','tsp-demo','wesco-company']:
            path = prefix+'/videos/'+slug+'/'
            content = (ROOT/path.lstrip('/')/'index.html').read_text(encoding='utf-8')
            data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',content,re.S).group(1))
            rows.append(f'<article><a href="{path}"><img src="{data["thumbnailUrl"][0]}" width="1280" height="720" loading="lazy" alt=""><h3>{e(data["name"])}</h3></a><p>{lang}</p></article>')
    return ''.join(rows)

def render_hub():
    title='TSP® 적용 전후·단상·삼상 설치 영상 | 6개 언어 | WESCO'
    desc='WESCO 순간정전보상장치 TSP® 적용 전후와 단상·삼상 설치·시운전 영상을 한국어, 영어, 간체중문, 번체중문, 일본어, 베트남어로 확인하세요.'
    schema={'@context':'https://schema.org','@type':'CollectionPage','name':title,'description':desc,'url':ORIGIN+'/videos/','mainEntity':{'@type':'ItemList','itemListElement':[{'@type':'ListItem','position':n+1,'url':ORIGIN+i['path'],'name':i['title']} for n,i in enumerate(ENTRIES)]}}
    out=head('ko',title,desc,'/videos/')+ld(schema)+'<script src="/videos/library.js" defer></script></head><body class="library-page"><a class="skip" href="#main">본문으로 이동</a>'+header('ko')
    out+='''<main id="main"><section class="library-hero"><p class="eyebrow">WESCO / VIDEO LIBRARY</p><h1>TSP를 이해하고,<br>설치와 시운전까지.</h1><p class="lead">순간정전보상장치 TSP®의 적용 전후부터 단상·삼상 설치까지.<br>고객과 현장 엔지니어를 위한 영상을 편한 언어로 만나보세요.</p><div class="library-meta"><span>3가지 주제</span><span>6개 언어 · 18편</span><span>공식 WESCO 채널</span></div></section><nav class="language-filter" aria-label="영상 언어 선택">'''
    for key,name in [('all','전체 / All')]+[(k,COPY[k]['name']) for k in ORDER]:
        out+=f'<button type="button" data-language-filter="{key}" aria-pressed="false">{name}</button>'
    out+='</nav><p id="filter-status" class="filter-note" role="status" aria-live="polite">전체 / All · 18편</p>'
    for locale in ORDER:
        c=COPY[locale]; items=[i for i in ENTRIES if i['locale']==locale]
        out+=f'<section class="language-section" data-video-language="{locale}" lang="{locale}" aria-labelledby="heading-{locale}"><div class="section-title"><h2 id="heading-{locale}">{c["name"]}</h2><span>{e(c["libraryTitle"])}</span></div><div class="cards">'+''.join(card(i) for i in items)+'</div></section>'
    out+='''<details class="legacy"><summary>제품소개·실제 데모·회사소개 영상 더 보기</summary><p>기존 한국어·영어 제품소개, 실제 데모 시연, WESCO 회사소개도 함께 확인하세요.</p><div class="cards">'''+legacy_cards()+'''</div></details><section class="library-context"><h2>우리 설비에는 어떻게 적용할까요?</h2><div class="two"><article><h3>반도체·디스플레이</h3><p>전압 변동에 민감한 공정과 제어전원의 보호 범위를 확인하세요.</p><ul><li><a href="/blog/semiconductor-fab-voltage-sag/">반도체 팹의 순간전압강하</a></li><li><a href="/blog/display-fab-power-quality/">디스플레이 라인의 전력품질</a></li></ul></article><article><h3>일반 제조업</h3><p>공정의 정지 요인과 설비 구성에 맞춰 적용 대상을 검토하세요.</p><ul><li><a href="/blog/smart-factory-power-quality/">스마트팩토리와 전력품질</a></li><li><a href="/blog/automotive-line-voltage-sag/">자동차 공장의 순간전압강하</a></li></ul></article></div></section><section class="video-cta"><p>설비에 맞는 TSP 적용 범위와 설치 구성을 상담하세요.</p><div class="video-cta-actions"><a class="video-cta-primary" href="https://tsp.wesco.works/ko/?s=video_library_ko#contact">TSP 도입 상담</a><a class="video-cta-secondary" href="https://tsp.wesco.works/ko/?s=video_library_ko#catalog">카탈로그 받기</a></div></section>'''
    out+=footer('ko')+'</main></body></html>\n'
    write('/videos/index.html',out)

def update_blog_links():
    changed=[]
    for locale, directory in [('ko', ROOT/'blog'), ('en', ROOT/'blog/en')]:
        for p in sorted(directory.glob('*/index.html')):
            if p.parent.name == 'en': continue  # English index is not an article.
            item=get_related_video(ROOT, p.parent.name, locale)
            old=p.read_text(encoding='utf-8')
            new, count=re.subn(r'<a class="rel discovery-video"[^>]*>.*?</a>',
                              lambda _: f'<a class="rel discovery-video" href="{e(item["path"])}">{e(item["label"])}</a>',
                              old, flags=re.S)
            if count != 1:
                raise BlogVideoConfigError(f'Expected one generated related-video link in {p.relative_to(ROOT)}; found {count}')
            if new!=old:
                p.write_text(new,encoding='utf-8'); changed.append(p.relative_to(ROOT).as_posix())
    return changed

def update_sitemap():
    # Preserve existing formatting and entries; replace only these 18 URLs.
    p=ROOT/'sitemap.xml'; source=p.read_text(encoding='utf-8')
    for item in ENTRIES:
        url=ORIGIN+item['path']
        source=re.sub(r'\s*<url>\s*<loc>'+re.escape(url)+r'</loc>.*?</url>','',source,flags=re.S)
    blocks=[]
    for item in ENTRIES:
        schema=video_schema(item); url=ORIGIN+item['path']
        lines=['  <url>',f'    <loc>{url}</loc>']
        for other in ENTRIES:
            if other['film']==item['film']:
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{other["locale"]}" href="{ORIGIN+other["path"]}"/>')
        default=next(i for i in ENTRIES if i['locale']=='en' and i['film']==item['film'])
        lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{ORIGIN+default["path"]}"/>')
        lines.append('    <video:video>')
        fields={'thumbnail_loc':schema['thumbnailUrl'][0],'title':schema['name'],'description':schema['description'],'player_loc':schema['embedUrl'],'publication_date':schema['uploadDate'],'duration':math.ceil(item['durationSeconds'])}
        lines += [f'      <video:{k}>{e(str(v))}</video:{k}>' for k,v in fields.items()]
        lines+=['    </video:video>','  </url>']; blocks.append('\n'.join(lines))
    source=re.sub(r'\s*</urlset>\s*$', '\n'+'\n'.join(blocks)+'\n</urlset>\n', source)
    ET.fromstring(source)
    p.write_text(source,encoding='utf-8')

if __name__=='__main__':
    for item in ENTRIES: render_watch(item)
    render_hub(); changed=update_blog_links(); update_sitemap()
    print(json.dumps({'watch_pages':len(ENTRIES),'languages':ORDER,'updated_blog_links':changed},ensure_ascii=False))
