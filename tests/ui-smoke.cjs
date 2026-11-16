// DOM integration against a real local HTTP server. This is not a visual browser test.
const {JSDOM, VirtualConsole} = require('jsdom');
const assert = require('node:assert/strict');
const base = process.env.STUDIO_TEST_URL || 'http://127.0.0.1:8088';
const errors = [];
const console = new VirtualConsole();
console.on('jsdomError', error => errors.push(error.message));
let cookie = '';
async function request(path, options={}) {
  const response = await fetch(new URL(path, base), {...options, headers:{...options.headers, Cookie:cookie}});
  const value = response.headers.get('set-cookie');
  if (value) cookie = value.split(';')[0];
  return response;
}
async function wait(condition, label, timeout=180000) {
  const started = Date.now();
  while (!condition()) {
    if (Date.now()-started > timeout) throw new Error('Timed out: '+label);
    await new Promise(resolve => setTimeout(resolve,50));
  }
}
(async () => {
  const dom = await JSDOM.fromURL(base, {resources:'usable',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:console,
    beforeParse(window) {
      window.fetch=request;
      window.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
      window.HTMLDialogElement.prototype.close=function(){this.open=false;};
    }});
  const document=dom.window.document;
  const $=selector=>document.querySelector(selector);
  const submit=selector=>$(selector).dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));
  await wait(()=>typeof dom.window.api === 'function','script loaded');
  await new Promise(resolve=>setTimeout(resolve,200));
  $('#password').value='lesson-demo-2026'; submit('#login-form');
  await wait(()=>$('#summary-strip').children.length===4,'learner loaded');
  assert.equal(document.querySelectorAll('[data-learner]').length,4);
  $('#run-button').click();
  await wait(()=>$('#run-summary').textContent.includes('Completed'),'real model run');
  await wait(()=>document.querySelectorAll('.finding-text').length===2,'profile rendering');
  $('[data-tab=profile]').click();
  assert.match($('.finding-text').textContent,/increased/);
  $('[data-source]').click(); assert.equal($('#source-dialog').open,true);
  assert.match($('#source-details').textContent,/Evidence ID/);
  $('[data-close=source-dialog]').click();
  $('[data-review=approve]').click();
  await wait(()=>$('#review-error').textContent.includes('note'),'empty note blocked');
  $('#review-note').value='Synthetic UI test: checked cited source assessments.';
  $('[data-review=approve]').click();
  await wait(()=>$('[data-review=release]'),'approval recorded');
  $('#review-note').value='Synthetic guardian conversation for automated UI testing only.';
  $('[data-review=release]').click();
  await wait(()=>$('#review-error').textContent.includes('Confirm'),'missing conversation blocked');
  $('#conversation').checked=true; $('[data-review=release]').click();
  await wait(()=>$('.download-link'),'released download visible');
  const report=await request($('.download-link').getAttribute('href'));
  assert.equal(report.status,200); assert.match(await report.text(),/Evidence:/);
  $('#new-learner-open').click();
  $('#new-name').value='<img src=x onerror=alert(1)>'; $('#new-school').value='Synthetic test school';
  $('#new-grade').value='6'; $('#new-consent').checked=true; submit('#new-learner-form');
  await wait(()=>$('#learner-title').textContent.includes('<img'),'new pseudonym escaped');
  assert.equal($('#learner-title').children.length,0);
  assert.equal($('#learner-nav').querySelectorAll('img').length,0);
  assert.deepEqual(errors,[]);
  process.stdout.write(JSON.stringify({status:'PASS',checks:['sign-in','learner rendering','real model run','profile rendering','citation dialog','empty review blocked','named approval','conversation required','released report','new learner','HTML escaping'],visual_layout_tested:false},null,2)+'\n');
  dom.window.close();
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
