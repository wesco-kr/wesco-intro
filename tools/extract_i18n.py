"""index.html 의 data-i18n 요소에서 한국어 사전(i18n/ko.json)을 뽑는다.
- data-i18n-attr → 그 속성값, data-i18n-html → innerHTML, 그 외 → 첫 비어있지 않은 직계 텍스트노드
- meta.* 키는 기존 ko.json 값을 재사용(없으면 HTML 값)
- 같은 키가 서로 다른 값으로 두 번 나오면 오류로 멈춘다
사용: python3 tools/extract_i18n.py [index.html] [i18n/ko.json]
"""
import sys, json, re
from html.parser import HTMLParser
src = sys.argv[1] if len(sys.argv) > 1 else "index.html"
dst = sys.argv[2] if len(sys.argv) > 2 else "i18n/ko.json"
html = open(src, encoding="utf-8").read()
VOID = {"br","hr","img","meta","link","input","source","wbr","area","base","col","embed","param","track"}

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]; self.out={}; self.pos=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        node={"tag":tag,"attrs":a,"text":None,"html_start":None}
        if "data-tk" in a:  # 썸네일 목차 라벨 (JS 가 data-t 를 data-i18n=data-tk 로 만든다)
            self.put(a["data-tk"], a.get("data-t",""))
        if "data-i18n" in a:
            key=a["data-i18n"]
            if "data-i18n-attr" in a:
                self.put(key,a.get(a["data-i18n-attr"],""))
            elif "data-i18n-html" in a:
                node["html_start"]=self.getpos(); node["key"]=key
            else:
                node["key"]=key
        if tag not in VOID: self.stack.append(node)
    def handle_data(self, data):
        if self.stack:
            n=self.stack[-1]
            if n.get("key") and n["html_start"] is None and n["text"] is None and data.strip():
                n["text"]=data.strip()
    def handle_endtag(self, tag):
        while self.stack:
            n=self.stack.pop()
            if n["tag"]==tag:
                if n.get("key"):
                    if n["html_start"] is not None:
                        # innerHTML: 원문에서 잘라낸다
                        s=self.rawdata_offset(n["html_start"]); e=self.rawdata_offset(self.getpos())
                        inner=html[s:e]; inner=inner[inner.index(">")+1:]
                        self.put(n["key"],re.sub(r"\s+"," ",inner).strip())
                    elif n["text"] is not None:
                        self.put(n["key"],n["text"])
                    else:
                        print("빈 텍스트:",n["key"],file=sys.stderr)
                break
    def rawdata_offset(self,pos):
        line,col=pos; return sum(len(l)+1 for l in html.split("\n")[:line-1])+col
    def put(self,k,v):
        if k in self.out and self.out[k]!=v:
            sys.exit(f"키 충돌 {k}: {self.out[k]!r} vs {v!r}")
        self.out[k]=v
p=P(); p.feed(html)
try: old=json.load(open(dst,encoding="utf-8"))
except Exception: old={}
d={}
for k,v in p.out.items():
    d[k]= old[k] if (k.startswith("meta.") and k in old) else v
# 스크립트가 만드는 키
d.setdefault("bar.fxOff","이펙트 OFF")
json.dump(d,open(dst,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print(f"{len(d)} keys -> {dst}")
