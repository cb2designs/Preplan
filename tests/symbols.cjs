const fs=require('fs'),assert=require('assert');
const catalog=JSON.parse(fs.readFileSync('static/symbols/catalog.json','utf8'));
assert.equal(catalog.length,17);assert.equal(new Set(catalog.map(s=>s.code)).size,17);
for(const s of catalog){
 assert(s.application.length>20);assert([15,16,17].includes(s.sourcePage));
 assert.equal(fs.readFileSync('static/symbols/'+s.asset,'utf8'),s.svg);
 assert(s.svg.includes('<path'));assert(!/<image|<script|href=/.test(s.svg));
}
const byCode=code=>catalog.find(s=>s.code===code);
assert.equal(byCode('ELEC').characteristics.background,'#005EB8');
assert.equal(byCode('CHILD').characteristics.foreground,'#005EB8');
assert.equal(byCode('CHILD').characteristics.background,'#FFFFFF');
assert.equal(byCode('SCBA').characteristics.field,'rectangular');
assert.equal(byCode('SCBA').characteristics.background,'#00843D');
assert.equal(byCode('NO-FIRE').characteristics.field,'circular');
assert.equal(byCode('NO-FIRE').characteristics.prohibition,'#C8102E');
for(const code of ['ARROW','ARROW-NE'])assert(byCode(code).characteristics.backgroundRule);
const source=fs.readFileSync('static/app.js','utf8');
const embedded=JSON.parse(source.split('const nfpaSymbols=')[1].split(';\n// END GENERATED SYMBOLS')[0]);
assert.deepEqual(embedded,catalog);
for(const id of ['FDC','FACP','SPR','TANK','KEY','ENT'])assert(source.includes("['"+id+"',"));
console.log('17 SVGs: vector-only assets, synchronized catalog, source pages, specified colors/fields, arrow rules, and legacy codes verified.');
