// Test UI w prawdziwej przegladarce (Edge headless + CDP, bez zaleznosci):
//   1) python-embed\WPy64-312101\python\python.exe tools\dev_server_5099.py
//   2) node tools\cdp_ui_check.js tools\cdp_scenarios\circuit_394.json
// Scenariusz = lista krokow {ev: wyrazenie JS, sleep: ms, shot: plik.png, sel: selektor}.
// Raportuje bledy JS strony; zrzuty laduja w biezacym katalogu (nie commitowac).
const { spawn } = require('child_process');
const fs = require('fs');
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const port = 9333;
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const proc = spawn(EDGE, ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`,
    '--window-size=1300,1700', '--user-data-dir=' + process.env.TEMP + '\\cdp_prof_' + Date.now(), 'about:blank'], { stdio: 'ignore' });
  let tabs;
  for (let i = 0; i < 40; i++) {
    try { tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (tabs.length) break; } catch (e) {}
    await sleep(500);
  }
  const page = tabs.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pend = {};
  const errs = [];
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; }
    else if (d.method === 'Runtime.exceptionThrown') errs.push('EXC ' + JSON.stringify(d.params.exceptionDetails.exception && d.params.exceptionDetails.exception.description || d.params.exceptionDetails.text).slice(0, 300));
    else if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errs.push('CONSOLE ' + JSON.stringify(d.params.args.map(a => a.value || a.description)).slice(0, 300)); };
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) return 'EXC: ' + JSON.stringify(r.result.exceptionDetails).slice(0, 400); return r.result.result.value; };
  const shot = async (file, sel) => {
    let clip;
    if (sel) {
      const box = await ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e) return null; const r=e.getBoundingClientRect(); return {x:r.x+scrollX,y:r.y+scrollY,w:r.width,h:r.height}})()`);
      if (box) clip = { x: box.x, y: box.y, width: Math.min(box.w, 1280), height: Math.min(box.h, 3200), scale: 1 };
    }
    const r = await send('Page.captureScreenshot', clip ? { format: 'png', clip, captureBeyondViewport: true } : { format: 'png' });
    fs.writeFileSync(file, Buffer.from(r.result.data, 'base64'));
  };
  await send('Page.enable'); await send('Runtime.enable');
  await send('Page.navigate', { url: 'http://127.0.0.1:5099/' });
  await sleep(4000);
  console.log('page ready:', await ev('typeof circuitCardHtml + "/" + typeof apiCall'));
  const scenario = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  for (const step of scenario) {
    if (step.ev) { const out = await ev(step.ev); console.log('EV', (step.name || ''), '=>', String(out).slice(0, 300)); }
    if (step.sleep) await sleep(step.sleep);
    if (step.shot) await shot(step.shot, step.sel);
  }
  console.log('JS ERRORS:', errs.length, errs.slice(0, 6).join(' || ')); ws.close(); proc.kill();
  process.exit(0);
})().catch(e => { console.log('ERR', e); process.exit(1); });
