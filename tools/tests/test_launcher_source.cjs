const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const code = fs.readFileSync(path.join(__dirname, '../../launcher.js'), 'utf8');
const sites = JSON.parse(fs.readFileSync(path.join(__dirname, '../../sites.json'), 'utf8'));
const contacts = sites.groups.flatMap(g => g.items).filter(i => ['inquiry','catalog'].includes(i.id));
function launcher(url, lang='ko') {
  const window = {};
  const context = {window, URL, location:new URL(url), document:{currentScript:null, documentElement:{lang}, body:null, addEventListener(){}},
    fetch:async()=>({ok:true,json:async()=>sites})};
  vm.runInNewContext(code,context);
  return window.WescoLauncher;
}
test('actual inquiry/catalogue routes identify their source section in each language',()=>{
  assert.equal(contacts.length,2);
  for (const [url, source] of [
    ['https://intro.wesco.works/?lang=en#p9','launcher_intro'],
    ['https://intro.wesco.works/blog/semiconductor-fab-voltage-sag/','launcher_blog'],
    ['https://intro.wesco.works/blog/en/','launcher_blog'],
    ['https://intro.wesco.works/videos/single-phase-installation/','launcher_videos'],
    ['https://intro.wesco.works/en/videos/tsp-demo/','launcher_videos'],
    ...['zh-cn','zh-tw','ja','vi'].map(l => [`https://intro.wesco.works/${l}/videos/single-phase-installation/`, 'launcher_videos']),
    ['https://intro.wesco.works/videos/#zh-TW','launcher_videos'],
    ['https://other.example/','site_launcher']]) {
    for (const [lang, destination] of [['ko','ko'],['en','en'],['zh-CN','cn'],['ja','en'],['vi','vn']]) {
      for(const item of contacts) {
        const out=new URL(launcher(url,lang).href(item.href));
        assert.equal(out.origin,'https://tsp.wesco.works');
        assert.equal(out.pathname,`/${destination}/`);
        assert.equal(out.searchParams.get('s'),source);
        assert.equal(out.hash,new URL(item.href.replace('{tsp}','ko')).hash);
      }
    }
  }
});
test('TSP source survives launcher navigation; invalid or absent source identifies only the menu',()=>{
  for(const source of ['video_single_phase_ko','A'.repeat(40),'nav_blog','', 'bad value', 'a'.repeat(41)]) {
    for(const item of contacts) {
      const out=new URL(launcher('https://tsp.wesco.works/en/?s='+encodeURIComponent(source),'zh-CN').href(item.href));
      assert.equal(out.searchParams.get('s'),/^[a-z0-9_-]{1,40}$/i.test(source)?source:'launcher_tsp');
      assert.equal(out.pathname,'/cn/');
    }
  }
});
test('only contact destinations change; explicit attribution and query/hash survive',()=>{
  const L=launcher('https://intro.wesco.works/videos/');
  for(const input of ['/blog/', 'https://example.com/ko/#contact', 'https://tsp.wesco.works.evil.example/ko/#contact',
    'http://tsp.wesco.works/ko/#contact','https://tsp.wesco.works/ko/','https://tsp.wesco.works/ko/#other']) assert.equal(L.href(input),input);
  const explicit='https://tsp.wesco.works/en/?s=video_single_phase_en&view=compact#contact';
  assert.equal(L.href(explicit),explicit);
  const added=new URL(L.href('https://tsp.wesco.works/en/?view=compact#catalog'));
  assert.equal(added.searchParams.get('view'),'compact');
  assert.equal(added.searchParams.get('s'),'launcher_videos');
  assert.equal(added.hash,'#catalog');
  assert.equal(new URL(launcher('https://tsp.wesco.works.evil.example/?s=spoof').href(contacts[0].href)).searchParams.get('s'),'site_launcher');
});
