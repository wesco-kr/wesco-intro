"""5개 언어 사전 검사 — 키 누락·HTML 태그 불일치·길이 폭주·미번역(한글 잔존).
사용: python3 tools/check_i18n.py
"""
import json, re, sys
ko = json.load(open("i18n/ko.json", encoding="utf-8"))
bad = 0
for lang in ["en", "cn", "jp", "vn"]:
    d = json.load(open(f"i18n/{lang}.json", encoding="utf-8"))
    miss = [k for k in ko if k not in d]
    extra = [k for k in d if k not in ko]
    hangul = [k for k, v in d.items() if re.search(r"[가-힣]", v) and not re.search(r"[가-힣]", "")]
    tags = [k for k in ko if sorted(re.findall(r"<[a-z]+>", ko[k])) != sorted(re.findall(r"<[a-z]+>", d.get(k, "")))]
    longk = [k for k in ko if k in d and len(d[k]) > max(12, len(ko[k]) * 2.2)]
    order = list(d) == list(ko)
    print(f"[{lang}] keys={len(d)} 누락={len(miss)} 잉여={len(extra)} 한글잔존={len(hangul)} 태그불일치={len(tags)} 과장={len(longk)} 순서일치={order}")
    for name, lst in [("누락", miss), ("잉여", extra), ("한글", hangul), ("태그", tags), ("과장", longk)]:
        if lst: print("   ", name, lst[:8])
    bad += len(miss) + len(extra) + len(hangul) + len(tags)
sys.exit(1 if bad else 0)
