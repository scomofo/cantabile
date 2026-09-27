/* global current, recording -- app globals read inside page.evaluate callbacks. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const path=require('node:path');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const root=path.resolve(__dirname,'..');
fs.mkdirSync(path.join(root,'research'),{recursive:true});
(async()=>{
 const server=spawn('python',[path.join(root,'app.py'),'--no-browser','--port','8774'],{cwd:root});
 await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{if(d.toString().includes('ready at'))resolve();});server.on('exit',c=>reject(Error('Server exited '+c)));setTimeout(()=>reject(Error('Server start timeout')),20000).unref();});
 let browser;
 try{
  browser=await chromium.launch({headless:true,executablePath:process.env.CANTABILE_CHROME||undefined,args:['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-audio-capture='+path.join(root,'tests/fixtures/mic-guide.wav')]});
  const context=await browser.newContext({viewport:{width:1440,height:1080},permissions:['microphone'],acceptDownloads:true});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('dialog',d=>d.accept());
  await page.goto('http://127.0.0.1:8774');await page.getByText('English neural voices ready',{exact:false}).waitFor();
  assert.equal(await page.locator('#sections .section-row').count(),5);
  for(const role of ['soprano','mezzo','alto','tenor','baritone','bass']){
   await page.locator('#new-role').selectOption(role);await page.locator('#add').click();
   assert.equal(await page.locator('#mode').inputValue(),'solo');
   await page.locator('#mode').selectOption('ensemble');assert.equal(await page.locator('#singers').inputValue(),'4');
   await page.locator('#mode').selectOption('solo');assert.equal(await page.locator('#singers').inputValue(),'1');
  }
  await page.locator('#voice').selectOption('hanami');assert.equal(await page.locator('#voice').inputValue(),'hanami');
  await page.locator('#voice').selectOption('tiger');assert.equal(await page.locator('#voice').inputValue(),'tiger');
  const before=await page.evaluate(()=>JSON.stringify(current().notes));
  await page.locator('#lyrics').fill('too few');await page.locator('#apply-lyrics').click();
  assert.equal(await page.evaluate(()=>JSON.stringify(current().notes)),before);
  await page.locator('#demo').click();
  // Actual female synthesis, mixing, download and audio decode through the UI.
  await page.locator('#render').click();await page.locator('#result').waitFor({state:'visible',timeout:120000});
  assert.match(await page.locator('#status').textContent(),/ready/i);
  await page.locator('#player').evaluate(a=>new Promise((res,rej)=>{if(a.readyState>=1)res();else{a.onloadedmetadata=res;a.onerror=rej;}}));
  assert((await page.locator('#player').evaluate(a=>a.duration))>20);
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#downloads a').first().click()]);
  await download.saveAs(path.join(root,'research/browser-mix.wav'));
  assert(fs.statSync(path.join(root,'research/browser-mix.wav')).size>100000);
  await page.locator('#new-role').selectOption('baritone');await page.locator('#add').click();
  // Keyboard activation and actual independent male synthesis.
  await page.locator('#audition').focus();await page.keyboard.press('Enter');
  await page.waitForFunction(()=>!document.getElementById('cancel').hidden);await page.waitForFunction(()=>document.getElementById('cancel').hidden,{},{timeout:120000});
  assert.match(await page.locator('#status').textContent(),/ready/i);
  // Real getUserMedia code path, using Chromium's synthetic microphone.
  await page.locator('#record').click();await page.waitForFunction(()=>document.getElementById('record-clock').textContent.startsWith('2.'));
  await page.locator('#record').click();assert(!(await page.locator('#use-notes').isDisabled()));
  assert(await page.evaluate(()=>recording===null));
  await page.locator('#use-notes').click();await page.getByText('Guide melody detected.',{exact:false}).waitFor();
  assert((await page.evaluate(()=>current().notes.length))>=1);
  // Imported recordings become a real source, and stale score changes are rejected.
  await page.locator('#use-stem').click();await page.waitForFunction(()=>document.getElementById('voice').value==='imported');
  assert.equal(await page.locator('#mode').inputValue(),'solo');
  await page.locator('#tempo').fill('89');await page.locator('#tempo').press('Tab');
  await page.locator('#audition').click();await page.waitForFunction(()=>document.getElementById('status').textContent.includes('changed since the WAV'));
  const [save]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);assert.match(save.suggestedFilename(),/\.json$/);
  // Restore a representative example for the screenshot.
  await page.locator('#demo').click();await page.locator('#new-role').selectOption('baritone');await page.locator('#add').click();await page.locator('#mode').selectOption('ensemble');
  await page.screenshot({path:path.join(root,'research/studio.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);
  console.log('PASS: choir ranges, solo/ensemble, male/female selection, lyric guard, actual vocal renders, WAV playback/download, keyboard render, mic capture, guide notes, imported voice, stale-stem guard, save and mobile layout.');
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
