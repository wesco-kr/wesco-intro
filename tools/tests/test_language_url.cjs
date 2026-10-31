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
  assert.equal(new URL(url,'https://intro.wesco.works').searchParams.get('lang'),lang==='ko'?null:lang);
}
console.log('PASS: 5 language routes, canonical/OG consistency, alternate locales, attribution/hash and history state preservation');
