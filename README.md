# WESCO 사업소개서

순간정전 보상장치 TSP® 25년 전문기업 — 책(사례집) 형식의 온라인 회사소개서.

**Live**: https://intro.wesco.works/

## 구성
- 13쪽 고정 판형(1120×720) — 표지 · 회사 소개 · 연혁 · 용도 · 사고 손실 · 사양서 요구 · 라인업 · 장점 · 개별·중앙 보상 · Sag-VIEWER · 글로벌 레퍼런스 · 글로벌 네트워크 · 뒷표지 (2026-09-15 축약판 → 09-17 3쪽 추가. 연혁은 대표이사 TI Malaysia 브리프(2026-06) 기준)
- 5개국어(한·영·중·일·베) — `i18n/<lang>.json`, 상단 언어 버튼 / `?lang=en` / 자동 감지
- 발표 모드(`p` 키 또는 `?present=1`) — 한 쪽씩 전체화면, ←→ 키·스와이프
- 이펙트(등장·카운트업·SLD 순간정전 시연) — 상단 버튼으로 끄기, `prefers-reduced-motion` 존중
- 디자인 컨셉: 「웜 스톤과 아이보리로 구성한 산업 전문서」(Astra 설계, 2026-09)

## 파일
| 경로 | 역할 |
|---|---|
| `index.html` | 본체 — 스타일·13쪽·스크립트 단일 파일 |
| `i18n.js`, `i18n/*.json` | 다국어 사전·적용기 |
| `tools/extract_i18n.py` | `index.html` → `i18n/ko.json` 키 추출 |
| `tools/check_i18n.py` | 4개 언어 누락·잉여·한글 잔존·태그 검사 |
| `tools/render_book.py` | 쪽별 PNG 렌더 + 넘침 검사 (`RENDER_BASE=http://127.0.0.1:8765` 로 http 경유 시 다국어) |
| `images/ci/` | 글로벌 레퍼런스 고객사 CI 106종(반도체·디스플레이·자동차·PCB·화학·2차전지·기타). 기본 `실적 CI.pptx`(2021-09) + 대표이사 Micron 브리프 2026 Ver 2.0E(2026-07)의 최신 10종(tsmc·UMC·Corning·Kia 신CI·HL Mando·Renault Korea·SK on·LG Energy Solution·SAMSUNG SDI·LG Innotek), 모두 `07-영업자료/07.제안자료/대표이사_출장_260609/`. 사내 자료에 로고가 없던 5종은 웹에서 수집 — onsemi(위키미디어 커먼즈 `Onsemi logo 2021.svg`), Nanya(nanya.com), Mosel Vitelic/MVC(moselvitelic.com), KINSUS(kinsus.com.tw), SI-FLEX(siflex.co.kr). 흰 배경 투명화. 미확보: LG-TORAY·Volta·MAX CHIP(사이트 접속 불가) |
| `images/proof/install_semi_2026.jpg` | 회사소개(p2) 현장 사진 — 원본 `07-영업자료/02.사진/00.설치사진/3상/WD-2026-CIP-150K.jpg`(2026 설치, 150kVA). 구 `install_semi.jpg`(2010년대)는 `all-new-intro.html`만 참조 |
| `images/og-image.jpg` | 링크 미리보기(카카오톡·메신저·SNS) 이미지 1200×630 — 워드마크 + TSP 라인업(`product/lineup_wide.png`) + 핵심 수치. 생성 `tools/make_og.py`(Pillow, 나눔스퀘어) |
| `images/world-map.png` | 글로벌 네트워크 지도 밑그림 — 본사→대리점 연결선·라벨은 `index.html` 안 SVG 오버레이(픽셀 실측 좌표) |
| `blog/` | 인사이트 글 (별도 유지) |
| `launcher.js` | 공용 사이트 런처. 다른 wesco.works 사이트도 `<script src="https://intro.wesco.works/launcher.js?v=1" defer data-mount="[data-wesco-launcher]">` 한 줄로 같은 서랍을 붙인다 |
| `sites.json` | WESCO 공개 사이트 목록 — 상단 「WESCO 사이트」 서랍과 뒷표지 「다음 단계」 카드가 이 한 파일을 읽는다. 사이트가 늘면 여기만 고친다. 사내·거래처 전용 시스템(quote·works·partner·cs)은 넣지 않는다 |

`_build/` 는 렌더 산출물·작업 로그로 git 에 올리지 않는다.

## 데이터 출처
WESCO-사업소개서-2025-Ver3.5 · 검증 수치만 사용(150,000+ Units · 900+ Companies · 15+ Countries · 2001년 설립)
글로벌 네트워크 거점은 `07-영업자료/13.대리점 관리/WESCO-대리점 LIST-V3.0.xlsx` 기준 — 대외 페이지에는 국가·도시만 표기하고 대리점 회사명은 넣지 않는다.

## Contact
- 영업: sh.han@wesco.co.kr
- 대표: wesco@wesco.co.kr
- 사이트: https://www.wesco.co.kr
