const fs = require('fs');
const js = fs.readFileSync('translations.js', 'utf8');
const html = fs.readFileSync('rejestr_usterek.html', 'utf8');

const used = new Set();
for (const m of html.matchAll(/data-i18n(?:-html|-placeholder|-title)?\s*=\s*"([^"]+)"/g)) used.add(m[1]);
for (const m of html.matchAll(/\bt\(\s*'([A-Za-z0-9_.]+)'/g)) used.add(m[1]);

eval(js + ';globalThis.__T = TRANSLATIONS;');
const TRANSLATIONS = globalThis.__T;

function lookup(lang, key) { return key.split('.').reduce((o,k)=>o&&o[k], TRANSLATIONS[lang]); }
const langs = ['pl','en','de'];
const missing = {pl:[], en:[], de:[]};
for (const k of used) for (const L of langs) if (lookup(L,k)===undefined) missing[L].push(k);
console.log('used keys:', used.size);
for (const L of langs) console.log('missing in', L, ':', JSON.stringify(missing[L], null, 0));

function flatKeys(obj, prefix='', out={}) {
  for (const [k,v] of Object.entries(obj)) {
    const p = prefix?prefix+'.'+k:k;
    if (v && typeof v==='object') flatKeys(v,p,out); else out[p]=1;
  }
  return out;
}
const plk = flatKeys(TRANSLATIONS.pl), enk = flatKeys(TRANSLATIONS.en), dek = flatKeys(TRANSLATIONS.de);
console.log('in pl missing in en:', JSON.stringify(Object.keys(plk).filter(k=>!(k in enk))));
console.log('in pl missing in de:', JSON.stringify(Object.keys(plk).filter(k=>!(k in dek))));
console.log('in en not in pl:', JSON.stringify(Object.keys(enk).filter(k=>!(k in plk))));
console.log('in de not in pl:', JSON.stringify(Object.keys(dek).filter(k=>!(k in plk))));
