const $ = (s) => document.querySelector(s);
const money = (n, cents = false) => new Intl.NumberFormat('en-US', {style:'currency', currency:'USD', maximumFractionDigits:cents ? 2 : 0, minimumFractionDigits:cents ? 2 : 0}).format(n);
const number = n => new Intl.NumberFormat('en-US', {maximumFractionDigits:1}).format(n);
let example, latest, revision = 0, timer, activeRequest;
const labels = {ffs:'Per visit', pmpm:'Per patient / month'};
function el(tag, text, className) { const node=document.createElement(tag); if(text !== undefined) node.textContent=text; if(className) node.className=className; return node; }
function metric(parent, name, value) { const row=el('div',undefined,'metric');row.append(el('span',name),el('b',value));parent.append(row); }
function collect() { return Object.fromEntries([...$('#scenario').querySelectorAll('input')].map(n=>[n.name,Number(n.value)])); }
function invalidate() { revision++; activeRequest?.abort(); latest=null; $('#results').hidden=true; $('#status').textContent='Inputs changed · recalculating…'; }
function preset(values) { for(const [key,value] of Object.entries(values)) $(`[name="${key}"]`).value=value; invalidate(); run(); }
async function run() {
  clearTimeout(timer);
  if(!$('#scenario').checkValidity()) { $('#results').hidden=true; $('#status').textContent='Enter valid values to calculate.'; return; }
  const current=++revision; activeRequest?.abort(); activeRequest=new AbortController();
  $('#error').hidden=true; $('#status').textContent='Calculating…';
  try {
    const started=performance.now();
    const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(collect()),signal:activeRequest.signal});
    const data=await response.json(); if(!response.ok) throw new Error(data.error || 'Calculation failed.');
    if(current!==revision) return;
    latest=data; render(data); $('#status').textContent=`Updated · ${Math.round(performance.now()-started)} ms request + calculation · deterministic results`; $('#results').hidden=false;
  } catch(error) { if(error.name==='AbortError'||current!==revision)return; $('#error').textContent=error.message;$('#error').hidden=false;$('#results').hidden=true;$('#status').textContent='No current result.'; }
}
function render(data) {
  const {inputs,baseline,stress,terms}=data;
  const over=stress.capacity_gap>1e-8;
  $('#capacity-banner').classList.toggle('warning',over);
  $('#capacity-title').textContent=over?'Demand exceeds appointment capacity':'Modeled demand fits appointment capacity';
  $('#capacity-detail').textContent=over?`${number(stress.capacity_gap)} additional monthly appointments would be needed in the stress case. A higher payment alone does not add capacity.`:`${number(inputs.capacity-stress.visits)} appointments remain in the stress case. This checks visit counts, not clinical staffing mix or quality.`;
  $('#capacity-number').textContent=`${number(stress.visits)} / ${number(inputs.capacity)}`;
  $('#contracts').replaceChildren(); $('#terms').replaceChildren();
  for(const model of ['ffs','pmpm']) {
    const base=baseline.contracts[model], risk=stress.contracts[model];
    const passes=base.feasible&&risk.feasible;
    const card=el('article',undefined,'contract'), top=el('div',undefined,'contract-top');
    top.append(el('h3',labels[model]),el('span',passes?'Both cases pass':'Constraints fail',`pill ${passes?'':'bad'}`));
    card.append(top,el('p',`${money(inputs[model==='ffs'?'ffs_rate':'pmpm_rate'],true)} ${model==='ffs'?'per completed visit':'per enrolled patient each month'}`,'offer'),el('div','Stress-case operating surplus','value-label'),el('div',money(risk.surplus),`value ${risk.surplus<0?'negative':''}`));
    const metrics=el('div',undefined,'metrics');
    metric(metrics,'Baseline surplus',money(base.surplus));metric(metrics,'Stress-case insurer spending',money(risk.payer_spend));metric(metrics,'Stress-case care delivery costs',money(risk.cost));metric(metrics,'Stress-case margin',risk.margin_pct===null?'Undefined (no revenue)':`${number(risk.margin_pct)}%`);
    const flags=el('div',undefined,'flags');
    for(const [key,label] of [['capacity_ok','Capacity'],['budget_ok','Budget'],['margin_ok','Target margin']]) { const ok=base[key]&&risk[key];flags.append(el('span',`${ok?'✓':'×'} ${label}`,`flag ${ok?'':'fail'}`)); }
    card.append(metrics,el('p','Checks across both baseline and stress cases','hint'),flags);$('#contracts').append(card);
    const term=terms[model], box=el('div',undefined,`term ${term.feasible?'':'infeasible'}`);
    box.append(el('h3',labels[model]),el('div',term.feasible?`${money(term.minimum_rate,true)}–${money(term.maximum_rate,true)}`:'No feasible terms','range'));
    if(term.feasible) box.append(el('p',`Lowest feasible payment: ${money(term.recommended_rate,true)}. Rates are rounded inward to whole cents.`));
    else for(const reason of term.reasons) box.append(el('p',reason));
    box.append(el('p',`Cost-only break-even: ${money(term.break_even_rate,true)}. With ${number(inputs.min_margin)}% target margin: at least ${money(term.minimum_rate,true)}. Budget ceiling: ${money(term.maximum_rate,true)}.`));
    $('#terms').append(box);
  }
  const rows=[['Expected visits',number(baseline.visits),number(stress.visits)],['Total care delivery costs',money(baseline.contracts.ffs.cost,true),money(stress.contracts.ffs.cost,true)],['Per-visit insurer payments',money(baseline.contracts.ffs.revenue,true),money(stress.contracts.ffs.revenue,true)],['Per-patient insurer payments',money(baseline.contracts.pmpm.revenue,true),money(stress.contracts.pmpm.revenue,true)],['Per-visit surplus',money(baseline.contracts.ffs.surplus,true),money(stress.contracts.ffs.surplus,true)],['Per-patient surplus',money(baseline.contracts.pmpm.surplus,true),money(stress.contracts.pmpm.surplus,true)]];
  $('#audit').replaceChildren(...rows.map(values=>{const row=el('tr');row.append(...values.map(v=>el('td',v)));return row;}));
  $('#assumptions').replaceChildren(...data.assumptions.map(a=>el('li',a)));
  chart(data);
}
function chart(data) {
  const svg=$('#chart');svg.replaceChildren();
  const add=(tag,attrs,text)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;svg.append(n);return n;};
  add('title',{},'Operating surplus across increasing monthly visit demand');
  add('desc',{},'Per-visit payments rise with visits; per-patient payments stay fixed. The audit table provides baseline and stress-case values.');
  const vals=data.sweep.flatMap(p=>[p.contracts.ffs.surplus,p.contracts.pmpm.surplus,0]);
  let lo=Math.min(...vals),hi=Math.max(...vals);const padding=Math.max((hi-lo)*.15,100);lo-=padding;hi+=padding;
  const max=data.sweep.at(-1).additional_visits_pct;
  const x=v=>78+v/max*610, y=v=>240-(v-lo)/(hi-lo)*220;
  for(let i=0;i<=4;i++){const value=lo+(hi-lo)*i/4;add('line',{x1:78,x2:688,y1:y(value),y2:y(value),stroke:'#e4ebe4'});add('text',{x:68,y:y(value)+4,'text-anchor':'end'},money(value));}
  add('line',{x1:78,x2:688,y1:y(0),y2:y(0),stroke:'#a6b9a9','stroke-dasharray':'4 4'});
  for(let i=0;i<=4;i++){const value=max*i/4;add('text',{x:x(value),y:263,'text-anchor':'middle'},`+${number(value)}%`);}
  add('text',{x:390,y:291,'text-anchor':'middle'},'Additional visits above baseline');
  const cap=(data.inputs.capacity/data.baseline.visits-1)*100;
  if(cap>=0&&cap<=max){add('line',{x1:x(cap),x2:x(cap),y1:20,y2:240,stroke:'#a78a65','stroke-dasharray':'5 5'});add('text',{x:Math.min(x(cap)+5,620),y:15},'Capacity');}
  for(const [model,color] of [['ffs','#256950'],['pmpm','#aa703b']]){
    add('polyline',{points:data.sweep.map(p=>`${x(p.additional_visits_pct)},${y(p.contracts[model].surplus)}`).join(' '),fill:'none',stroke:color,'stroke-width':3});
    add('circle',{cx:x(data.inputs.stress_pct),cy:y(data.stress.contracts[model].surplus),r:5,fill:color,stroke:'white','stroke-width':2});
  }
}
async function init(){
  try {
    const responses=await Promise.all([fetch('/api/schema'),fetch('/api/example')]);if(responses.some(r=>!r.ok))throw new Error('Could not load the calculator.');
    const [schema,fixture]=await Promise.all(responses.map(r=>r.json()));example=fixture;
    const groups={patients:'PATIENTS & CAPACITY',fixed_cost:'COST OF CARE',ffs_rate:'PAYMENT OFFERS',min_margin:'PLANNING GUARDRAILS'};
    for(const [name,rule] of Object.entries(schema.properties)){
      if(groups[name])$('#fields').append(el('div',groups[name],'field-group'));
      const label=el('label',undefined,'field'),input=el('input');input.type='number';input.name=name;input.min=rule.minimum;input.max=rule.maximum;input.step=rule.type==='integer'?'1':'any';input.required=true;input.value=example[name];label.append(el('span',rule.title),input);$('#fields').append(label);
    }
    $('#scenario').addEventListener('submit',e=>{e.preventDefault();run();});
    $('#scenario').addEventListener('input',()=>{invalidate();clearTimeout(timer);timer=setTimeout(run,250);});
    $('#reset').addEventListener('click',()=>preset(example));
    $('#capacity-demo').addEventListener('click',()=>preset({...example,stress_pct:70}));
    $('#budget-demo').addEventListener('click',()=>preset({...example,payer_budget:45000}));
    $('#download').addEventListener('click',()=>{if(!latest)return;const url=URL.createObjectURL(new Blob([JSON.stringify(latest,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download='carebalance-scenario.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
    await run();
  } catch(e){$('#status').textContent='Unable to start.';$('#error').textContent=e.message;$('#error').hidden=false;}
}
init();
