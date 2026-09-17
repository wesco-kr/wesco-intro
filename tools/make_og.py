"""링크 미리보기용 OG 이미지(1200×630) 생성 — images/og-image.jpg. 실행: python3 tools/make_og.py"""
from PIL import Image, ImageDraw, ImageFont
import os; R=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','images')+'/'
W,H=1200,630
bg=Image.new('RGBA',(W,H),(253,252,249,255))
d=ImageDraw.Draw(bg)
d.rectangle([0,H-10,W,H],fill=(225,67,27,255))
p=Image.open(R+'product/lineup_wide.png').convert('RGBA')
pw=660; ph=int(p.height*pw/p.width); p=p.resize((pw,ph),Image.LANCZOS)
bg.alpha_composite(p,(W-pw-24,(H-10-ph)//2+8))
wm=Image.open(R+'wesco_wordmark.png').convert('RGBA')
ww=300; wh=int(wm.height*ww/wm.width); wm=wm.resize((ww,wh),Image.LANCZOS)
bg.alpha_composite(wm,(60,86))
NB='/usr/share/fonts/truetype/nanum/NanumSquareB.ttf'; NR='/usr/share/fonts/truetype/nanum/NanumSquareR.ttf'
DJ='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
f40=ImageFont.truetype(NB,40); f36=ImageFont.truetype(NB,36); fR=ImageFont.truetype(NR,22); fS=ImageFont.truetype(NB,21)
fReg=ImageFont.truetype(DJ,18)
STONE=(68,64,60,255); BROWN=(87,83,78,255); RED=(225,67,27,255); MUTE=(138,132,125,255)
x=62; y=86+wh+52
d.text((x,y),'TSP',font=f40,fill=RED); tw=d.textlength('TSP',font=f40)
d.text((x+tw+3,y-2),'®',font=fReg,fill=RED)
d.text((x,y+56),'순간정전·순간전압강하',font=f36,fill=STONE)
d.text((x,y+106),'보상장치 전문기업',font=f36,fill=STONE)
d.text((x,y+180),'배터리 없는 EDLC 방식',font=fR,fill=BROWN)
d.text((x,y+214),'단상 0.5kVA ~ 삼상 2,400kVA',font=fR,fill=BROWN)
d.text((x,y+248),'25년 · 150,000대+ · 900+ 고객사 · 15개국+',font=fR,fill=BROWN)
d.text((x,H-56),'intro.wesco.works',font=fS,fill=MUTE)
bg.convert('RGB').save(R+'og-image.jpg',quality=88,optimize=True)

import os; print(os.path.getsize(R+'og-image.jpg'))
