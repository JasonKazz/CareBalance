const $=s=>document.querySelector(s);
const money=(n,cents=false)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:cents?2:0,maximumFractionDigits:cents?2:0}).format(n);
const count=n=>new Intl.NumberFormat('en-US',{maximumFractionDigits:1}).format(n);
const signed=n=>(n>0?'+':'')+money(n);
const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let contract=null,activity='',extraction=null,report=null,baseReport=null,confirmedRates=[],revision=0,working=false,timer;
const setStatus=text=>$('#status').textContent=text;
function error(text){$('#error').textContent=text;$('#error').hidden=!text;}
function resetReport(){revision++;report=null;baseReport=null;confirmedRates=[];$('#report').hidden=true;$('#review-confirm').checked=false;$('#uplift').value=0;$('#uplift-value').textContent='0%';}
function invalidateContract(){resetReport();extraction=null;$('#review').hidden=true;error('');}
function bytes64(bytes){let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);}
async function post(path,data){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let result;try{result=await response.json();}catch{throw new Error('The local server did not return a result. Check that it is running.');}if(!response.ok)throw new Error(result.error||'Request failed.');return result;}
function busy(on){working=on;for(const id of ['extract','demo','compare'])$('#'+id).disabled=on;}
function updateMode(){$('#consent-label').hidden=$('#mode').value!=='gemini';invalidateContract();}
async function readContract(file){if(!file)return;if(file.size>4*1024*1024)throw new Error('Contract must be no larger than 4 MB.');contract={name:file.name,content:bytes64(new Uint8Array(await file.arrayBuffer()))};$('#contract-name').textContent=file.name;invalidateContract();setStatus('Contract ready. Add activity and extract the proposed rates.');}
async function readActivity(file){if(!file)return;if(file.size>500000)throw new Error('Activity CSV must be no larger than 500 KB.');activity=await file.text();$('#activity-name').textContent=file.name;resetReport();setStatus('Activity loaded. Review extracted rates before comparison.');}
async function extractContract(){
 if(working)return;error('');if(!contract){error('Choose a contract first, or try the fictional sample.');return;}
 if($('#mode').value==='gemini'&&!$('#consent').checked){error('Confirm the Google processing disclosure before using Gemini.');return;}
 resetReport();const version=revision;busy(true);setStatus($('#mode').value==='gemini'?'Gemini is reading the offer. Rates still require your review…':'Reading structured schedule rows locally…');
 try{const result=await post('/api/extract',{...contract,mode:$('#mode').value,consent:$('#consent').checked});if(version!==revision)return;extraction=result;renderReview();setStatus(result.rates.length?`${result.rates.length} proposed rates found. Review their sources, select applicable rates, and confirm.`:'No supported rates found. Use CODE | DESCRIPTION | USD RATE text rows, or try Gemini for a prose offer.');}
 catch(e){if(version===revision)error(e.message);setStatus('Extraction did not complete. No rates were assumed.');}finally{busy(false);}
}
function renderReview(){
 $('#review').hidden=false;$('#review-rows').replaceChildren();$('#step2').classList.add('current');
 $('#method-label').textContent=extraction.mode==='gemini'?'Gemini extraction':'Local row parser';
 const supported=extraction.rates.filter(r=>r.source_supported).length;
 $('#extraction-summary').textContent=`${extraction.rates.length} rate candidates · ${supported} quotes located with code and amount · ${extraction.pages.length} page(s).`+(extraction.usage?` API estimate: $${extraction.usage.estimated_usd.toFixed(4)}.`:'');
 for(const row of extraction.rates){
  const tr=node('tr');tr.dataset.id=row.id;
  const use=node('input');use.type='checkbox';use.checked=row.source_supported&&!row.ambiguous;use.setAttribute('aria-label','Use '+row.code);
  const selectCell=node('td');selectCell.append(use);const code=node('td');code.append(node('strong',row.code),node('small',row.description));
  const rate=node('input');rate.type='number';rate.min=0;rate.max=1000000;rate.step='.01';rate.value=row.rate.toFixed(2);rate.setAttribute('aria-label','Proposed rate for '+row.code);
  const rateCell=node('td');rateCell.append(rate);const evidence=node('td');const button=node('button',`Page ${row.page} ↗`,'source-button');button.type='button';button.addEventListener('click',()=>showSource(row));
  const badge=node('small',row.ambiguous?'Multiple alternatives: choose one':row.source_supported?'Quote found · review applicability':'Quote not supported · review required',row.ambiguous||!row.source_supported?'warn':'');
  evidence.append(button,badge);tr.append(selectCell,code,rateCell,evidence);$('#review-rows').append(tr);
  use.addEventListener('change',resetReport);rate.addEventListener('input',()=>{resetReport();badge.textContent=Number(rate.value)===row.rate?'Original extracted rate':'Edited by you · quote does not validate this rate';});
 }
 $('#extract-limits').replaceChildren(...extraction.limitations.map(t=>node('li',t)));
}
function showSource(row){
 $('#source-title').textContent=`${row.code} · page ${row.page}`;
 $('#source-note').textContent='Extracted document text. Highlighting shows the cited passage when it can be located exactly. Confirm rates and all conditions against the original document.';
 const text=extraction.pages.find(p=>p.page===row.page)?.text||'';const index=text.indexOf(row.quote);const pre=$('#source-text');pre.replaceChildren();
 if(index>=0){pre.append(document.createTextNode(text.slice(0,index)),node('mark',row.quote),document.createTextNode(text.slice(index+row.quote.length)));}
 else pre.textContent=text+'\n\nCITED QUOTE (spacing may differ):\n'+row.quote;
 $('#source-dialog').showModal();
}
function selectedRates(){return [...$('#review-rows').children].filter(tr=>tr.querySelector('input[type=checkbox]').checked).map(tr=>{const source=extraction.rates.find(r=>r.id===Number(tr.dataset.id));const input=tr.querySelector('input[type=number]');if(input.value===''||!input.checkValidity())throw new Error('Enter valid USD rates with at most two decimals.');return {code:source.code,rate:input.value,source_id:source.id,edited:Number(input.value)!==source.rate};});}
async function compare(){
 if(working)return;error('');if(!activity){error('Upload the activity CSV first.');return;}if(!$('#review-confirm').checked){error('Review the selected rates and check the confirmation before comparison.');return;}
 const version=++revision;busy(true);setStatus('Repricing the matched historical service basket…');
 try{const rates=selectedRates();const result=await post('/api/reprice',{activity_csv:activity,rates,confirmed:true});if(version!==revision)return;confirmedRates=rates;baseReport=result;report=result;$('#uplift').value=0;$('#uplift-value').textContent='0%';renderReport();setStatus('Comparison ready. Every amount is calculated from your confirmed rates and CSV.');$('#report').scrollIntoView({behavior:'smooth',block:'start'});}
 catch(e){error(e.message);$('#report').hidden=true;}finally{busy(false);}
}
function renderReport(){
 const summary=report.summary;$('#report').hidden=false;$('#step3').classList.add('current');const uplift=Number($('#uplift').value);
 $('#report-scope').textContent=`${summary.matched_services} of ${summary.total_services} service codes matched · ${count(summary.matched_volume)} annual services modeled · USD`;
 $('#current-total').textContent=money(summary.current_matched);$('#proposed-total').textContent=money(summary.proposed_matched);$('#delta-total').textContent=signed(summary.annual_delta);$('#delta-total').className=summary.annual_delta<0?'negative':'positive';
 $('#delta-pct').textContent=summary.change_pct===null?'No nonzero baseline for percentage comparison':`${summary.change_pct>0?'+':''}${count(summary.change_pct)}% versus current · matched services only`;
 $('#proposal-label').textContent=uplift?'COUNTEROFFER SCENARIO':'PROPOSED SCHEDULE';
 $('#insight-title').textContent=summary.annual_delta<0?'The matched service basket would reimburse less.':summary.annual_delta>0?'The matched service basket would reimburse more.':'The matched service basket breaks even.';
 const biggest=[...report.matched].sort((a,b)=>Math.abs(b.annual_delta)-Math.abs(a.annual_delta))[0];
 $('#insight-body').textContent=`${biggest.code} contributes ${signed(biggest.annual_delta)} of the annual change. ${report.unmatched.length?`${report.unmatched.length} unmatched code(s) remain outside the proposed total.`:'All activity codes are matched.'}${uplift?' This view includes your hypothetical rate increase.':''}`;
 $('#coverage-heading').textContent=`${summary.matched_services} / ${summary.total_services} codes matched`;
 $('#coverage-description').textContent=`${count(summary.volume_coverage_pct)}% of annual service volume; ${summary.revenue_coverage_pct===null?'baseline reimbursement coverage undefined':count(summary.revenue_coverage_pct)+'% of current reimbursement'}.`;
 const base=baseReport.summary;$('#negotiation-note').textContent=base.uniform_uplift_to_break_even_pct===null?'The confirmed proposal totals zero. A percentage increase cannot close a nonzero dollar gap.':base.annual_delta<0?`The original matched offer needs approximately ${count(base.uniform_uplift_to_break_even_pct)}% higher rates uniformly to equal the current total, before per-rate cent rounding.`:'The original matched offer already meets or exceeds the current total. Explore a higher-rate scenario without changing the source offer.';
 $('#impact-rows').replaceChildren();
 for(const row of report.matched){const tr=node('tr');const service=node('td');service.append(node('strong',row.code),node('small',row.description));tr.append(service,node('td',count(row.annual_volume)),node('td',money(row.current_rate,true)),node('td',money(row.proposed_rate,true)),node('td',signed(row.annual_delta),row.annual_delta<0?'negative':'positive'));const source=node('td');const confirmed=confirmedRates.find(r=>r.code===row.code);const found=extraction.rates.find(r=>r.id===confirmed.source_id);const button=node('button',`p.${found.page} · CSV row ${row.csv_row}`,'source-button');button.addEventListener('click',()=>showSource(found));source.append(button);if(confirmed.edited||uplift)source.append(node('small',uplift?'Hypothetical uplift applied':'User-edited rate','warn'));tr.append(source);$('#impact-rows').append(tr);}
 $('#unmatched-label').textContent=`${report.unmatched.length} unmatched activity codes · ${report.unused_contract_codes.length} unused offer codes`;
 $('#unmatched-list').replaceChildren(...report.unmatched.map(r=>node('p',`${r.code} — ${count(r.annual_volume)} services; current annual reimbursement ${money(r.current_annual)}. Proposed reimbursement unknown.`)));
 if(report.unused_contract_codes.length)$('#unmatched-list').append(node('p','Offer codes absent from activity: '+report.unused_contract_codes.join(', ')));
 $('#report-limits').replaceChildren(...report.limitations.map(t=>node('li',t)));
 drawImpact(report.matched);drawCoverage(summary.volume_coverage_pct);
}
function svgElement(svg,tag,attrs,text){const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);if(text!==undefined)el.textContent=text;svg.append(el);return el;}
function drawImpact(rows){const svg=$('#impact-chart');svg.replaceChildren();const items=[...rows].sort((a,b)=>Math.abs(b.annual_delta)-Math.abs(a.annual_delta)).slice(0,8);const h=items.length*43+38;svg.setAttribute('viewBox',`0 0 720 ${h}`);svgElement(svg,'title',{},'Largest annual changes by service; all matched values appear in the audit table');const max=Math.max(1,...items.map(r=>Math.abs(r.annual_delta)));const zero=370,scale=230/max;svgElement(svg,'line',{x1:zero,x2:zero,y1:5,y2:h-30,stroke:'#c9d5bf'});items.forEach((row,i)=>{const y=i*43+10;const width=Math.abs(row.annual_delta)*scale;svgElement(svg,'text',{x:10,y:y+18},row.code);svgElement(svg,'rect',{x:row.annual_delta<0?zero-width:zero,y,width:Math.max(width,1),height:27,rx:4,fill:row.annual_delta<0?'#c79772':'#688f64'});svgElement(svg,'text',{x:705,y:y+18,'text-anchor':'end'},signed(row.annual_delta));});svgElement(svg,'text',{x:zero,y:h-7,'text-anchor':'middle'},'$0');}
function drawCoverage(percent){const svg=$('#coverage-chart');svg.replaceChildren();svgElement(svg,'circle',{cx:90,cy:90,r:64,fill:'none',stroke:'#e8eedf','stroke-width':11});const c=2*Math.PI*64;svgElement(svg,'circle',{cx:90,cy:90,r:64,fill:'none',stroke:'#718e5f','stroke-width':11,'stroke-dasharray':`${c*percent/100} ${c}`,'stroke-linecap':'round',transform:'rotate(-90 90 90)'});svgElement(svg,'text',{x:90,y:93,'text-anchor':'middle',fill:'#395332','font-size':31,'font-family':'system-ui'},`${Math.round(percent)}%`);svgElement(svg,'text',{x:90,y:114,'text-anchor':'middle',fill:'#8d9b7f','font-size':9,'font-family':'system-ui'},'ANNUAL VOLUME');}
async function counteroffer(){if(!baseReport)return;const version=++revision;const uplift=Number($('#uplift').value);$('#uplift-value').textContent=`${uplift}%`;$('#export').disabled=true;setStatus('Updating hypothetical counteroffer…');try{const next=await post('/api/reprice',{activity_csv:activity,rates:confirmedRates,confirmed:true,uplift_pct:uplift});if(version!==revision)return;report=next;renderReport();setStatus(uplift?'Hypothetical counteroffer shown. Source contract rates are unchanged.':'Original confirmed offer restored.');}catch(e){if(version===revision){error(e.message);$('#report').hidden=true;}}finally{if(version===revision)$('#export').disabled=false;}}
async function demo(){if(working)return;error('');try{const responses=await Promise.all([fetch('/samples/offer.txt'),fetch('/samples/activity.csv')]);if(responses.some(r=>!r.ok))throw new Error('Sample files unavailable.');const [offer,csv]=await Promise.all(responses.map(r=>r.text()));contract={name:'Fictional Harbor Clinic offer.txt',content:bytes64(new TextEncoder().encode(offer))};activity=csv;$('#contract-name').textContent=contract.name;$('#activity-name').textContent='Fictional annual activity.csv';$('#mode').value='local';$('#consent').checked=false;$('#consent-label').hidden=true;invalidateContract();await extractContract();$('#review').scrollIntoView({behavior:'smooth'});}catch(e){error(e.message);}}
$('#demo').addEventListener('click',demo);$('#extract').addEventListener('click',extractContract);$('#compare').addEventListener('click',compare);$('#mode').addEventListener('change',updateMode);$('#close-source').addEventListener('click',()=>$('#source-dialog').close());
$('#contract-file').addEventListener('change',async e=>{try{await readContract(e.target.files[0]);}catch(err){invalidateContract();contract=null;error(err.message);}});
$('#activity-file').addEventListener('change',async e=>{try{await readActivity(e.target.files[0]);}catch(err){resetReport();activity='';error(err.message);}});
$('#uplift').addEventListener('input',()=>{revision++;$('#export').disabled=true;$('#uplift-value').textContent=`${$('#uplift').value}%`;clearTimeout(timer);timer=setTimeout(counteroffer,180);});
$('#export').addEventListener('click',()=>{if(!report)return;const value={analysis:report,confirmed_rates:confirmedRates,counteroffer_uplift_pct:Number($('#uplift').value),source_evidence:extraction.rates,extraction_limitations:extraction.limitations};const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=node('a');a.href=url;a.download='carebalance-contract-analysis.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
fetch('/api/config').then(r=>r.json()).then(config=>{$('#gemini-option').disabled=!config.gemini_available;$('#provider-status').textContent=config.gemini_available?'Gemini available. Local mode reads CODE | DESCRIPTION | USD RATE rows.':'Local mode reads CODE | DESCRIPTION | USD RATE rows. Add GEMINI_API_KEY to .env and reload to enable Gemini.';}).catch(()=>error('Cannot reach the local server. Start CareBalance and reload.'));
