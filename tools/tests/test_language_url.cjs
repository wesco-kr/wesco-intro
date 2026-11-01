const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[2], 'utf8');
const fn = source.slice(source.indexOf('  function syncLanguageUrl'), source.indexOf('  async function setLang'));
const locales = {ko:'ko_KR',en:'en_US',cn:'zh_CN',jp:'ja_JP',vn:'vi_VN'};
for (const [lang, locale] of Object.entries(locales)) {
  const attrs = {};
  const alternatives = [];
  let url;
  const state = {slide: 9};
  const context = { URL, location:{href:'https://intro.wesco.works/?s=blog&lang=en#p9'},
    history:{state,replaceState(s, unused, u){assert.equal(s,state);url=u;}},
    document:{querySelector(selector){return {setAttribute(k,v){attrs[selector+':'+k]=v;}};},
      querySelectorAll(){return [{remove(){}}];},
      createElement(){const el={setAttribute(k,v){el[k]=v;}};return el;},
      head:{appendChild(el){alternatives.push(el.content);}}}};
  vm.runInNewContext(fn+'\nsyncLanguageUrl('+JSON.stringify(lang)+');',context);
  const expected='https://intro.wesco.works/'+(lang==='ko'?'':'?lang='+lang);
  assert.equal(attrs['link[rel="canonical"]:href'],expected);
  assert.equal(attrs['meta[property="og:url"]:content'],expected);
  assert.equal(attrs['meta[property="og:locale"]:content'],locale);
  assert.equal(alternatives.length,4);
  assert.ok(!alternatives.includes(locale));
  assert.ok(url.includes('s=blog') && url.endsWith('#p9'));
  assert.equal(new URL(url,'https://intro.wesco.works').searchParams.get('lang'),lang);
  // Simulate reopening the rewritten URL with a conflicting saved/browser language.
  const initial = source.slice(source.indexOf('  function getInitialLang()'), source.indexOf('  // 261003'));
  for (const blocked of [false,true]) {
    const reopened={URLSearchParams,location:{search:new URL(url,'https://intro.wesco.works').search},
      localStorage:{getItem(){if(blocked)throw Error('blocked');return 'en';}},navigator:{language:'en-US'}};
    assert.equal(vm.runInNewContext("const SUPPORTED=['ko','en','cn','jp','vn']; const DEFAULT_LANG='ko'; const STORAGE_KEY='wesco-intro-lang';"+initial+'getInitialLang();',reopened),lang);
  }
}
// A canonical URL must resolve to its own language regardless of preferences.
const initial = source.slice(source.indexOf('  function getInitialLang()'), source.indexOf('  // 261003'));
let canonicalCases = 0;
for (const browser of ['ko-KR','en-US','zh-CN','ja-JP','vi-VN']) {
  for (const saved of ['ko','en','cn','jp','vn',null]) {
    for (const blocked of [false,true]) {
      for (const search of ['', '?s=blog', '?lang=invalid', '?lang=']) {
        const context = {URLSearchParams,location:{search},navigator:{language:browser},
          localStorage:{getItem(){if(blocked)throw Error('blocked');return saved;}}};
        assert.equal(vm.runInNewContext("const SUPPORTED=['ko','en','cn','jp','vn']; const DEFAULT_LANG='ko'; const STORAGE_KEY='wesco-intro-lang';"+initial+'getInitialLang();',context),'ko');
        canonicalCases++;
      }
    }
  }
}
console.log(`PASS: 5 language routes and 240 bare-root/invalid-language preference cases; canonical/OG consistency, reload, attribution/hash and history state preservation (${canonicalCases} cases)`);
