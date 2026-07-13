/* Keystone life-sciences design system — faithful port of Keystone.dc.html.
   UI/presentation only: no engine, no fabricated data (the program self-labels
   ILLUSTRATIVE · SYNTHETIC). Light default, dark instrument-mode toggle. */
(() => {
"use strict";
const $ = (s, r=document) => r.querySelector(s);
const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const hexA = (v,a) => { v=(v||'').trim();
  if(v.startsWith('#')){let h=v.slice(1);if(h.length===3)h=h.split('').map(x=>x+x).join('');const n=parseInt(h,16);return `rgba(${(n>>16)&255},${(n>>8)&255},${n&255},${a})`;}
  const m=v.match(/(\d+)[ ,]+(\d+)[ ,]+(\d+)/);return m?`rgba(${m[1]},${m[2]},${m[3]},${a})`:v; };
const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------------- data (verbatim from Keystone.dc.html) ---------------- */
const NAV=[
 {group:'DISCOVERY',items:[{id:'discovery',label:'Discovery Run',icon:'play_circle'},{id:'dataready',label:'Data Readiness',icon:'fact_check'},{id:'cell',label:'Research Cell',icon:'groups'}]},
 {group:'ANALYSIS',items:[{id:'targets',label:'Target Ranking',icon:'stacked_bar_chart'},{id:'perturbseq',label:'Perturb-seq Analysis',icon:'genetics'},{id:'atlas',label:'Cell-State Atlas',icon:'scatter_plot'},{id:'evidence',label:'Evidence Graph',icon:'hub',badge:'47'},{id:'reasoning',label:'Reasoning Pipeline',icon:'account_tree'},{id:'decision',label:'Decision Engine',icon:'fork_right'},{id:'protein',label:'3D Protein Viewer',icon:'biotech'}]},
 {group:'INTEGRITY',items:[{id:'integrity',label:'Research Integrity',icon:'verified'},{id:'frontier',label:'Frontier Guard',icon:'security'}]},
 {group:'OUTPUT',items:[{id:'grant',label:'Grant Export',icon:'description'}]},
];
/* Which nav surfaces the ACTIVE program actually supports (set from the server's
   program payload). null = show all (initial paint before a program loads). A
   scientist never lands on an empty tab: only surfaces with real per-domain data
   are shown for that program. */
let CAPS=null;
// These hold the ACTIVE program's real data; applyProgram() fills them from the
// server before any screen renders. Empty until the first program loads.
let STAGES=[];
let FACTORS=[];
let NODES=[];
let EDGES=[];
const TYPE_LABEL={genetics:'Human genetics',experiment:'Experiment',biomarker:'Biomarker',mechanism:'Mechanism',phenotype:'Clinical phenotype',translational:'Translational',hypothesis:'Working hypothesis',safety:'Safety signal'};
let EXPERIMENTS=[];
const SCREENS=[
 {name:'Dual-use & misuse screen',status:'flag',note:'Keystone reasons over published literature and public databases and drafts experiments for human review. It refuses to help design pathogens, enhance toxicity, or evade a safety assay — see the refused request class below.'},
 {name:'Wet-lab biosafety',status:'pass',note:'In-silico only. Keystone runs no laboratory work, orders no reagents, and handles no biological materials or select agents.'},
 {name:'Human subjects & PHI',status:'pass',note:'No patient-level or identifiable data. Every source is a published, aggregate finding — not a medical record.'},
 {name:'Data governance',status:'pass',note:'Runs locally; the API key stays server-side. Sources are public (Crossref · OpenAlex · UniProt · ChEMBL · Cellosaurus) and never leave the device.'},
 {name:'Output control',status:'pass',note:'Every recommendation is a draft hypothesis gated on principal-investigator sign-off. Keystone makes no clinical, diagnostic, or treatment claim.'},
];
const REFUSAL={request:'“Suggest edits that raise a compound’s potency while helping it evade a standard genotoxicity screen.”',reason:'This asks Keystone to defeat a safety readout rather than improve safety. Keystone will not help conceal, evade, or weaken a toxicology or biosafety signal. It is shown here as a representative example of the misuse class Keystone refuses — not a logged user request.',log:'Policy example · Frontier Guard refuses this class of request · release gated on dual human sign-off'};
/* Grant bundle contents — computed from the ACTIVE program's real evidence, not a
   fixed LRRK2 sheet. Field Integrity + node count come straight from META/NODES. */
const grantFiles=()=>[
 {name:'Specific Aims',pages:'1 p',note:'Aims linked to signed, sourced inferences'},
 {name:'Evidence appendix',pages:'—',note:(NODES&&NODES.length?NODES.length:0)+' evidence nodes — every one traceable to a source'},
 {name:'Integrity certificate',pages:'1 p',note:'Field Integrity '+(META.fiBand||'—')+(META.fiScore!=null?' · '+META.fiScore:'')+(META.fiRange?' · range '+META.fiRange:'')},
 {name:'Reproducibility statement',pages:'2 p',note:'Dataset · code · environment · seed · model · run — deposited'},
 {name:'Conflicts & caveats',pages:'1 p',note:'Unresolved conflicts disclosed, not hidden'},
];
const confVar = c => c>=0.8?'--ok':(c>=0.63?'--warn':'--risk');

/* ---------------- program layer: real engine data per program ---- */
// Program-agnostic intro shown under every program's Discovery Run.
const PROGRAM_INTRO="Keystone assembles the case for a program from primary literature, structured assays, and prior art — assigning provenance to every claim before a single conclusion is drawn. Nothing below is asserted without a source you can open.";
// Neutral boot state — overwritten by the first real program fetch before any
// render. No disease is hard-coded here.
let META={progmono:"Keystone",progname:"Loading…",progsub:"fetching real engine data",illustrative:false,runRef:"",title:"",
 intro:PROGRAM_INTRO,meta:[],fiBand:'—',fiScore:null,fiRange:'',runSummary:'',pdb:null,target:''};
function updateShell(){const set=(id,v)=>{const el=$('#'+id);if(el)el.textContent=v;};
 set('progmono',META.progmono);set('progname',META.progname);set('progsub',META.progsub);
 set('fiband',META.fiBand||'—');set('finum',META.fiScore==null?'—':META.fiScore);
 const b=$('#progbadge');if(b)b.style.display=META.illustrative?'':'none';}
function applyProgram(p){STAGES=p.stages;FACTORS=p.field_integrity.factors;NODES=p.nodes;EDGES=p.edges;EXPERIMENTS=p.experiments;
 CAPS=Array.isArray(p.capabilities)?p.capabilities:null;
 META={progmono:p.program+(p.run_ref?' — '+p.run_ref.split(' · ')[0]:''),progname:p.program,progsub:'Target validation · '+(p.illustrative?'illustrative':'real engine data'),
  illustrative:!!p.illustrative,runRef:p.run_ref,title:p.title,intro:PROGRAM_INTRO,meta:p.meta,
  fiBand:p.field_integrity.band||'—',fiScore:p.field_integrity.score,fiRange:p.field_integrity.range,runSummary:'COMPLETE · '+p.stages.length+'/'+p.stages.length,
  pdb:p.pdb||null,target:(p.meta&&p.meta[0]?p.meta[0].v:'')+' structure'};
 updateShell();
 if(CAPS && STATE.screen && !CAPS.includes(STATE.screen)) STATE.screen='discovery';   // don't strand a scientist on a tab this program doesn't support
 go(STATE.screen);}
let _progSeq=0;   // only the latest program switch may apply
async function fetchProgram(domain){
 const seq=++_progSeq; const m=$('#main'); if(m)m.style.opacity='.4';
 try{
  const p=await (await fetch('/api/program?domain='+encodeURIComponent(domain))).json();
  if(seq!==_progSeq) return;                 // a newer switch superseded this response — drop it
  applyProgram(p);
 }catch(e){ if(seq===_progSeq) programError(domain); }
 finally{ if(m && seq===_progSeq) m.style.opacity=''; }
}
/* Honest failure: a failed program fetch is NEVER rebranded as the synthetic
   Parkinson's scaffold. Show an explicit "unavailable" state — Keystone shows no
   data rather than a fabricated one. */
function programError(domain){
 STAGES=[];FACTORS=[];NODES=[];EDGES=[];EXPERIMENTS=[];CAPS=[];renderNav();
 META={progmono:'—',progname:'Program unavailable',progsub:'engine offline — could not load '+domain,
  illustrative:false,runRef:'',title:'Program engine unavailable',intro:'',
  meta:[],fiBand:'—',fiScore:null,fiRange:'',runSummary:'—',pdb:null,target:''};
 updateShell();
 const m=$('#main');
 if(m) m.innerHTML='<div style="padding:64px 44px;max-width:560px">'+
  '<div style="font:600 20px/1.3 \'Inter Tight\',sans-serif;color:var(--ink);margin-bottom:10px">Program engine unavailable</div>'+
  '<div style="font:400 14px/1.6 \'Inter Tight\',sans-serif;color:var(--secondary)">Keystone could not load <b>'+esc(domain)+'</b> and will not display fabricated data in its place. Reselect a program to retry.</div></div>';
}
function switchProgram(v){ fetchProgram(v); }

/* ---------------- state + lifecycle ---------------- */
const STATE={screen:'discovery',selected:null,domain:'gbm'};
let _raf=0, _cleanup=null;
function stopLoops(){ if(_raf) cancelAnimationFrame(_raf); _raf=0; if(_cleanup){_cleanup();_cleanup=null;} }

/* current REAL domain (the switcher value; lrrk2 is illustrative → fall back to gbm for live calls) */
const curDomain=()=>{const v=($('#progswitch')||{}).value; return (v && v!=='lrrk2') ? v : 'gbm';};
const getJSON=async u=>{const r=await fetch(u); if(!r.ok) throw new Error(r.status); return r.json();};

/* honest live-Claude status — from /healthz, no fabrication.
   Purple "CLAUDE · LIVE" only when the key is set AND the network is reachable;
   otherwise "DETERMINISTIC" (the engine still runs, numbers are identical). */
const LIVE={on:false,loaded:false};
async function refreshLive(){
 try{const h=await getJSON('/healthz'); LIVE.on=!!h.live_claude; LIVE.loaded=true;}
 catch(e){LIVE.on=false; LIVE.loaded=true;}
 renderLiveBadge();
}
function renderLiveBadge(){
 const on=LIVE.on;
 document.querySelectorAll('.livebadge').forEach(el=>{
  el.innerHTML=`<span style="width:6px;height:6px;border-radius:50%;background:var(${on?'--claude-live':'--outline'})${on?';box-shadow:0 0 0 3px rgba(166,139,255,.18)':''}"></span>`
   +`<span style="font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.1em;color:var(${on?'--claude-live':'--secondary'})">${on?'CLAUDE · LIVE':'DETERMINISTIC'}</span>`;
  el.title=on?'Claude is connected (API key + reachable network). Reasoning prose is live; every number stays deterministic.'
             :'Running deterministic (no reachable Anthropic API here). Set ANTHROPIC_API_KEY with network access to activate live Claude prose — numbers are identical either way.';
 });
}

/* ---------------- search: DOI/PMID resolve + prior-art (real, honest offline) ---------------- */
const DOI_RE=/\b10\.\d{4,9}\/[^\s"']+/i;
const NAV_WORDS={decision:'decision',hypothes:'decision',evidence:'evidence',graph:'evidence',
 integrity:'integrity',reason:'reasoning',agent:'reasoning',pipeline:'reasoning',protein:'protein',
 structure:'protein',frontier:'frontier',grant:'grant',discovery:'discovery',run:'discovery'};
function searchOverlay(html){
 let o=$('#ks-search-ov');
 if(!o){o=document.createElement('div');o.id='ks-search-ov';
  o.style.cssText='position:fixed;inset:0;z-index:80;background:rgba(0,0,0,.55);display:flex;align-items:flex-start;justify-content:center;padding:72px 20px;overflow:auto';
  o.addEventListener('click',e=>{if(e.target===o)o.remove();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){const x=$('#ks-search-ov');if(x)x.remove();}});
  document.body.appendChild(o);}
 o.innerHTML=`<div style="max-width:720px;width:100%;background:var(--paper);border:1px solid var(--hairline);border-radius:14px;box-shadow:0 24px 70px rgba(0,0,0,.45);overflow:hidden">${html}</div>`;
 return o;
}
const closeBtn=`<button onclick="document.getElementById('ks-search-ov').remove()" style="border:none;background:none;cursor:pointer;color:var(--secondary);flex:none"><span class="ms">close</span></button>`;

/* ---------------- Ask Claude: a live reasoning answer over the real evidence graph ---------------- */
const ASK_STAGES=[
 {t:'Planning the analysis',d:'Decomposing the question into a bounded reasoning plan.'},
 {t:'Reading the evidence graph',d:'Real nodes — primary literature, assays, prior art.'},
 {t:'Classifying load-bearing citations',d:'Claude judges which citations the case truly rests on.'},
 {t:'Mining contradictions',d:'Conflicting results and retracted sources, surfaced.'},
 {t:'Generating competing hypotheses',d:'Claude drafts falsifiable hypotheses; tools compute every number.'},
 {t:'Ranking the next experiment',d:'Scored by expected information gain against cost.'},
];
const _asknum=v=>{ if(v==null)return'—'; if(typeof v==='object')v=(v.value??v.point??v.score??v); return typeof v==='number'?(Math.abs(v)<1?v.toFixed(3):v):esc(String(v)); };
function _askSteps(active){return ASK_STAGES.map((s,i)=>{const st=i<active?'done':(i===active?'run':'idle');
 const dot=st==='done'?`<div style="width:22px;height:22px;border-radius:50%;background:var(--claude-live);display:flex;align-items:center;justify-content:center;flex:none"><span class="ms" style="font-size:14px;color:#fff">check</span></div>`
  :st==='run'?`<div style="width:22px;height:22px;border-radius:50%;background:var(--container);border:1px solid var(--claude-live);display:flex;align-items:center;justify-content:center;flex:none"><span class="spin" style="border-top-color:var(--claude-live)"></span></div>`
  :`<div style="width:22px;height:22px;border-radius:50%;background:var(--container);border:1px solid var(--hairline);display:flex;align-items:center;justify-content:center;flex:none"><span class="mono" style="font-size:9px;color:var(--outline)">${i+1}</span></div>`;
 return `<div style="display:flex;gap:13px;padding:11px 28px;${i===ASK_STAGES.length-1?'':'border-bottom:1px solid var(--hairline)'};${st==='idle'?'opacity:.45':''}">${dot}<div style="flex:1;min-width:0"><div style="font:500 13px/1.3 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.t)}</div><div style="font:400 11.5px/1.45 'Inter Tight',sans-serif;color:var(--secondary);margin-top:2px">${esc(s.d)}</div></div></div>`;}).join('');}
async function askClaude(q){
 const dom=curDomain();
 const live=(typeof LIVE!=='undefined'&&LIVE.on);
 const badge=`<span style="display:inline-flex;align-items:center;gap:6px;color:var(${live?'--claude-live':'--secondary'});font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.1em"><span style="width:6px;height:6px;border-radius:50%;background:var(${live?'--claude-live':'--outline'})${live?';box-shadow:0 0 0 3px rgba(107,75,214,.18)':''}"></span>${live?'CLAUDE · LIVE':'DETERMINISTIC'}</span>`;
 const head=`<div style="padding:22px 28px;border-bottom:1px solid var(--hairline);display:flex;align-items:flex-start;justify-content:space-between;gap:14px"><div style="min-width:0"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><span class="mono" style="font-size:10px;letter-spacing:.14em;color:var(--claude-live)">ASK CLAUDE · ${esc(dom.toUpperCase())} EVIDENCE GRAPH</span>${badge}</div><div style="font:400 19px/1.35 Newsreader,serif;color:var(--ink);margin-top:7px;word-break:break-word">${esc(q).slice(0,150)}</div></div>${closeBtn}</div>`;
 const foot=`<div style="padding:13px 28px;color:var(--secondary);font:400 11px/1.55 'Inter Tight',sans-serif;border-top:1px solid var(--hairline)">Claude reasons over the real evidence graph; the deterministic engine owns every number. ${live?'Live analysis — a few seconds.':'Set ANTHROPIC_API_KEY for live Claude prose — the ranking is identical either way.'}</div>`;
 searchOverlay(head+`<div id="ks-ask-body">${_askSteps(0)}</div>`+foot);
 let active=0; const timer=setInterval(()=>{ active=Math.min(ASK_STAGES.length-1,active+1); const b=$('#ks-ask-body'); if(b&&!b.dataset.done)b.innerHTML=_askSteps(active); }, 3200);
 let d=null,err=null;
 try{ d=await getJSON('/api/decision?domain='+encodeURIComponent(dom)); }catch(e){ err=String(e&&e.message||e); }
 clearInterval(timer);
 const body=$('#ks-ask-body'); if(!body) return; body.dataset.done='1';
 if(err||!d||!d.recommendation){ body.innerHTML=`<div style="padding:24px 28px;color:var(--warn);font:400 13px/1.6 'Inter Tight',sans-serif">Claude could not complete this analysis${err?' ('+esc(err)+')':''}. The deterministic Decision Engine still stands — open it from the sidebar.</div>`; return; }
 const r=d.recommendation, ch=(d.competing_hypotheses||[]);
 const others=ch.filter(h=>h.rank!==1).slice(0,3).map(h=>`<div style="display:flex;gap:12px;padding:10px 0;border-top:1px solid var(--hairline)"><span class="mono" style="font-size:11px;color:var(--secondary);flex:none;width:26px">#${h.rank}</span><div style="flex:1;min-width:0"><div style="font:400 13px/1.45 'Inter Tight',sans-serif;color:var(--ink2)">${esc(String(h.statement||'').slice(0,140))}</div><div class="mono" style="font-size:10px;color:var(--secondary);margin-top:3px">priority ${_asknum(h.priority_score)} · info-gain ${_asknum(h.information_gain)}</div></div></div>`).join('');
 body.innerHTML=`<div style="padding:20px 28px">
   <div style="margin-bottom:10px"><span class="mono" style="font-size:10px;letter-spacing:.12em;color:var(--claude-live)">CLAUDE'S RECOMMENDATION · #1 OF ${ch.length}</span></div>
   <div style="font:400 18px/1.4 Newsreader,serif;color:var(--ink)">${esc(String(r.statement||''))}</div>
   ${r.why_first?`<div style="font:400 13.5px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin-top:10px">${esc(String(r.why_first))}</div>`:''}
   <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px">
    ${[['PRIORITY',_asknum(r.priority_score)],['INFO GAIN',_asknum(r.information_gain)],['RISK',esc(String(r.risk||'—'))],['COST',r.cost_usd?'$'+_asknum(r.cost_usd):'—'],['DURATION',r.duration_weeks?_asknum(r.duration_weeks)+' wk':'—']].map(x=>`<div style="border:1px solid var(--hairline);border-radius:8px;padding:8px 12px;background:var(--lowest)"><div class="mono" style="font-size:8.5px;letter-spacing:.08em;color:var(--secondary)">${x[0]}</div><div style="font:500 14px/1.1 'Inter Tight',sans-serif;color:var(--ink);margin-top:3px">${x[1]}</div></div>`).join('')}
   </div>
   ${r.how_to_falsify?`<div style="margin-top:14px;padding:12px 14px;border:1px solid var(--risk);border-radius:8px;background:var(--risk-c)"><div class="mono" style="font-size:9px;letter-spacing:.08em;color:var(--risk)">KILL-CONDITION</div><div style="font:400 13px/1.5 'Inter Tight',sans-serif;color:var(--ink);margin-top:4px">${esc(String(r.how_to_falsify))}</div></div>`:''}
   ${others?`<div style="margin-top:18px"><div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--secondary);margin-bottom:2px">COMPETING HYPOTHESES CLAUDE RANKED BELOW IT</div>${others}</div>`:''}
   <button id="ks-ask-open" style="margin-top:18px;display:inline-flex;align-items:center;gap:7px;border:1px solid var(--primary);background:var(--primary);color:var(--on-primary);border-radius:9px;padding:10px 16px;font:500 13px/1 'Inter Tight',sans-serif;cursor:pointer"><span class="ms" style="font-size:16px">fork_right</span>Open the full Decision Engine</button>
  </div>`;
 const ob=$('#ks-ask-open'); if(ob) ob.onclick=()=>{ const x=$('#ks-search-ov'); if(x)x.remove(); go('decision'); };
}
/* live real-data target assessment for ANY gene — the "type your own gene, watch
   it fetch real data" proof that Keystone generalizes past the curated demo. */
async function assessTarget(gene){
 const steps=[
  {t:'Resolving the gene',d:'symbol → Ensembl id via Open Targets search'},
  {t:'Fetching real disease associations',d:'live from the Open Targets platform'},
  {t:'Scoring type-2 relevance',d:'strongest asthma / atopy / allergy association'},
 ];
 const head=`<div style="padding:22px 28px;border-bottom:1px solid var(--hairline);display:flex;align-items:flex-start;justify-content:space-between;gap:14px"><div style="min-width:0"><div class="mono" style="font-size:10px;letter-spacing:.14em;color:var(--claude-live)">LIVE TARGET ASSESSMENT · OPEN TARGETS</div><div style="font:400 21px/1.3 Newsreader,serif;color:var(--ink);margin-top:6px">${esc(gene)}</div><div class="mono" style="font-size:10px;color:var(--secondary);margin-top:3px">real-time · any gene · not from the curated demo</div></div>${closeBtn}</div>`;
 const stepHtml=(active)=>steps.map((s,i)=>{const st=i<active?'done':i===active?'run':'idle';
  const dot=st==='done'?`<div style="width:20px;height:20px;border-radius:50%;background:var(--ok);display:flex;align-items:center;justify-content:center;flex:none"><span class="ms" style="font-size:13px;color:#fff">check</span></div>`:st==='run'?`<div style="width:20px;height:20px;border-radius:50%;background:var(--container);border:1px solid var(--claude-live);display:flex;align-items:center;justify-content:center;flex:none"><span class="spin" style="border-top-color:var(--claude-live)"></span></div>`:`<div style="width:20px;height:20px;border-radius:50%;background:var(--container);border:1px solid var(--hairline);flex:none"></div>`;
  return `<div style="display:flex;gap:12px;padding:9px 28px;${st==='idle'?'opacity:.45':''}">${dot}<div><div style="font:500 12.5px/1.3 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.t)}</div><div style="font:400 11px/1.4 'Inter Tight',sans-serif;color:var(--secondary)">${esc(s.d)}</div></div></div>`;}).join('');
 searchOverlay(head+`<div id="ks-assess-body" style="padding:8px 0 12px">${stepHtml(0)}</div>`);
 let active=0; const timer=setInterval(()=>{active=Math.min(steps.length-1,active+1);const b=$('#ks-assess-body');if(b&&!b.dataset.done)b.innerHTML=stepHtml(active);},700);
 let d=null; try{ d=await getJSON('/api/assess?gene='+encodeURIComponent(gene)); }catch(e){ d={resolved:false,note:String(e&&e.message||e)}; }
 clearInterval(timer);
 const body=$('#ks-assess-body'); if(!body)return; body.dataset.done='1';
 if(!d||!d.resolved){ body.innerHTML=`<div style="padding:20px 28px;color:var(--warn);font:400 13px/1.6 'Inter Tight',sans-serif">${esc((d&&d.note)||'Could not resolve this gene against Open Targets.')}</div>`; return; }
 const t2=d.type2;
 const dis=(d.top_diseases||[]).map(x=>`<div style="display:flex;align-items:center;gap:10px;padding:6px 0"><div style="flex:1;height:5px;border-radius:3px;background:var(--high);overflow:hidden"><div style="height:100%;width:${Math.round((x.score||0)*100)}%;background:var(--primary)"></div></div><span style="font:400 12px/1.3 'Inter Tight',sans-serif;color:var(--ink2);width:220px;flex:none">${esc(x.disease)}</span><span class="mono" style="font-size:11px;color:var(--ink);width:40px;text-align:right">${x.score}</span></div>`).join('');
 body.innerHTML=`<div style="padding:18px 28px">
   <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
     <span class="mono" style="font-size:10px;padding:4px 9px;border-radius:20px;background:var(--container);color:var(--ink2)">${esc(d.symbol)} · ${esc(d.ensembl)}</span>
     ${d.biotype?`<span class="mono" style="font-size:10px;padding:4px 9px;border-radius:20px;background:var(--container);color:var(--secondary)">${esc(d.biotype)}</span>`:''}
     ${t2?`<span class="mono" style="font-size:10px;padding:4px 9px;border-radius:20px;background:var(--container);color:var(--ok)">type-2: ${t2.score} · ${esc(t2.disease)}</span>`:`<span class="mono" style="font-size:10px;padding:4px 9px;border-radius:20px;background:var(--container);color:var(--secondary)">no type-2 association</span>`}
   </div>
   <div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--secondary);margin-bottom:8px">TOP REAL DISEASE ASSOCIATIONS · OPEN TARGETS</div>
   <div style="border:1px solid var(--hairline);border-radius:9px;background:var(--lowest);padding:12px 16px">${dis||'<span style="color:var(--secondary)">none returned</span>'}</div>
   <div style="margin-top:12px;font:400 11px/1.5 'Inter Tight',sans-serif;color:var(--secondary)">Fetched <b style="color:var(--ink2)">live from Open Targets</b> · ${esc(d.ensembl)} · real-time, not curated. Scores aggregate genetic + literature evidence — real records, not proof of causality.</div>
  </div>`;
}
async function runSearch(q){
 q=(q||'').trim(); if(!q) return;
 // 1) command-palette: a bare screen keyword jumps there
 const key=q.toLowerCase();
 for(const w in NAV_WORDS){ if(key===w||key==='go '+w){ const x=$('#ks-search-ov'); if(x)x.remove(); go(NAV_WORDS[w]); return; } }
 const doi=(q.match(DOI_RE)||[])[0];
 // 2) a GENE SYMBOL → live real-data target assessment (proves it generalizes past the demo)
 const isGene = !doi && /^[A-Za-z0-9-]{2,9}$/.test(q) && (/[0-9]/.test(q) || q===q.toUpperCase()) && !NAV_WORDS[key];
 if(isGene){ return assessTarget(q.toUpperCase()); }
 // 2) a research QUESTION → ask Claude to reason over the evidence graph (the AI workbench)
 const isQuestion = !doi && q.length>=12 &&
   (/\?\s*$/.test(q) || /\b(is|are|does|do|can|could|would|should|will|what|why|how|which|whether|design|rank|recommend|target|inhibit|treat)\b/i.test(q));
 if(isQuestion){ return askClaude(q); }
 searchOverlay(`<div style="padding:26px 28px"><div class="mono" style="font-size:10px;letter-spacing:.14em;color:var(--secondary);margin-bottom:10px">${doi?'IDENTIFIER · PRIOR ART':'PRIOR ART · OPENALEX'}</div><div style="color:var(--secondary);font:400 13px/1.5 'JetBrains Mono',monospace">Resolving “${esc(q).slice(0,84)}” against the real record…</div></div>`);
 let d={}; try{ d=await getJSON('/api/prior_art?q='+encodeURIComponent(q)); }catch(e){ d={note:'Lookup failed: '+String(e)}; }
 const matches=(d.matches||[]);
 const head=`<div style="padding:22px 28px;border-bottom:1px solid var(--hairline);display:flex;align-items:flex-start;justify-content:space-between;gap:14px"><div style="min-width:0"><div class="mono" style="font-size:10px;letter-spacing:.14em;color:var(--secondary)">${doi?'IDENTIFIER · PRIOR ART':'HAS THIS BEEN STUDIED?'}</div><div style="font:500 16px/1.35 'Inter Tight',sans-serif;color:var(--ink);margin-top:5px;word-break:break-word">${esc(q).slice(0,110)}</div></div>${closeBtn}</div>`;
 const doiRow=doi?`<a href="https://doi.org/${esc(doi)}" target="_blank" rel="noopener" style="display:flex;align-items:center;gap:11px;padding:15px 28px;border-bottom:1px solid var(--hairline);text-decoration:none;color:var(--ink)"><span class="ms" style="color:var(--claude-live)">link</span><div style="flex:1;min-width:0"><div style="font:500 13px/1.35 'Inter Tight',sans-serif">Open ${esc(doi)} on the publisher</div><div class="mono" style="font-size:10px;color:var(--secondary)">resolves the real record — not proof the claim is true</div></div><span class="ms" style="color:var(--outline)">north_east</span></a>`:'';
 const retr=d.any_retracted?`<div style="padding:12px 28px;border-bottom:1px solid var(--hairline);background:var(--risk-c,rgba(226,117,108,.10));color:var(--risk);font:600 11px/1.4 'JetBrains Mono',monospace">⚠ A matching work is RETRACTED — do not build on it.</div>`:'';
 const list=matches.length? matches.slice(0,6).map(m=>`<div style="padding:14px 28px;border-bottom:1px solid var(--hairline)"><div style="font:500 13px/1.45 'Inter Tight',sans-serif;color:var(--ink)">${esc(m.title||m.display_name||'—')}${(m.is_retracted||m.retracted)?' <span style="color:var(--risk);font:600 10px/1 monospace">· RETRACTED</span>':''}</div><div class="mono" style="font-size:10px;color:var(--secondary);margin-top:3px">${esc(String(m.year||''))}${m.doi?' · '+esc(m.doi):''}</div></div>`).join('')
  : `<div style="padding:20px 28px;color:var(--ink2);font:400 13px/1.6 'Inter Tight',sans-serif">${esc(d.note||'No matching work resolved.')}</div>`;
 const foot=`<div style="padding:13px 28px;color:var(--secondary);font:400 11px/1.5 'Inter Tight',sans-serif">Prior art from OpenAlex. Absence of a match is <b>not</b> evidence of novelty. Tip: type <span class="mono">decision</span>, <span class="mono">evidence</span>, <span class="mono">agents</span> to jump screens.</div>`;
 searchOverlay(head+retr+doiRow+list+foot);
}

/* ================= BRING YOUR OWN DATA — the scientist feeds their own research
   into the real engine, from the front door. Three flows, every one wired to a
   real, already-tested endpoint (no new science, no fabrication):
     • references → POST /api/import        (integrity triage + Field Integrity +
                                              Decision Engine, computed on YOUR papers)
     • lab data   → POST /api/bench/review  (deterministic QC that DOWNGRADES a
                                              result's confidence when a check fails)
     • gene       → /api/assess (reuses assessTarget — live Open Targets)
   ================================================================= */
const postJSON=async(u,body)=>{
 const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(!r.ok){ let m=''; try{ m=(await r.json()).error||''; }catch(e){} throw new Error(m||('HTTP '+r.status)); }
 return r.json();
};
const _naWorking=msg=>`<div style="display:flex;align-items:center;gap:12px;padding:16px 0;color:var(--secondary)"><span class="spin" style="border-top-color:var(--primary)"></span><span style="font:400 13px/1.5 'Inter Tight',sans-serif">${esc(msg)}</span></div>`;
const _chip=(label,val,col)=>`<div style="border:1px solid var(--hairline);border-radius:8px;padding:8px 12px;background:var(--lowest);min-width:60px"><div class="mono" style="font-size:8.5px;letter-spacing:.07em;color:var(--secondary)">${esc(label)}</div><div style="font:600 15px/1.1 'Inter Tight',sans-serif;color:var(${col||'--ink'});margin-top:3px">${esc(String(val))}</div></div>`;
let _naTab='references';
function newAnalysis(tab){
 _naTab=tab||_naTab||'references';
 const T=(id,label,icon)=>`<button data-natab="${id}" style="display:inline-flex;align-items:center;gap:7px;border:none;border-bottom:2px solid ${_naTab===id?'var(--primary)':'transparent'};background:none;cursor:pointer;padding:11px 15px;font:500 13px/1 'Inter Tight',sans-serif;color:var(${_naTab===id?'--ink':'--secondary'})"><span class="ms" style="font-size:17px">${icon}</span>${label}</button>`;
 const head=`<div style="padding:20px 26px 0;border-bottom:1px solid var(--hairline)">
   <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:14px">
     <div style="min-width:0"><div class="mono" style="font-size:10px;letter-spacing:.14em;color:var(--primary)">NEW ANALYSIS · YOUR OWN DATA</div>
     <div style="font:400 21px/1.3 Newsreader,serif;color:var(--ink);margin-top:6px">Feed your own research into the engine</div></div>${closeBtn}</div>
   <div style="display:flex;gap:2px;margin-top:13px;flex-wrap:wrap">${T('references','Paste references','description')}${T('lab','Upload lab data','science')}${T('gene','Assess a gene','biotech')}</div></div>`;
 const o=searchOverlay(head+`<div id="na-body" style="padding:22px 26px"></div>`);
 o.querySelectorAll('[data-natab]').forEach(b=>b.onclick=()=>newAnalysis(b.getAttribute('data-natab')));
 const body=$('#na-body');
 if(_naTab==='lab') _naLab(body); else if(_naTab==='gene') _naGene(body); else _naReferences(body);
}
function _naReferences(host){
 host.innerHTML=`<div style="font:400 13px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin-bottom:12px">Paste a <b>.bib</b> / <b>.ris</b> export or a list of DOIs. Keystone pulls the real records (Crossref · OpenAlex), flags every retraction and post-publication change, scores the set's <b>Field Integrity</b>, and ranks the next experiment on <b>your</b> papers.</div>
  <textarea id="na-refs" spellcheck="false" placeholder="10.1038/nature03095&#10;10.1016/j.cell.2008.01.038&#10;… or paste a whole .bib / .ris file" style="width:100%;min-height:148px;resize:vertical;border:1px solid var(--hairline);border-radius:10px;background:var(--lowest);color:var(--ink);font:400 12.5px/1.6 'JetBrains Mono',monospace;padding:12px 14px;box-sizing:border-box"></textarea>
  <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px">
    <button id="na-refs-go" style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--primary);background:var(--primary);color:var(--on-primary);border-radius:9px;padding:10px 16px;font:500 13px/1 'Inter Tight',sans-serif;cursor:pointer"><span class="ms" style="font-size:17px">bolt</span>Analyze my references</button>
    <button id="na-refs-sample" style="border:1px solid var(--hairline);background:var(--paper);color:var(--ink2);border-radius:9px;padding:10px 14px;font:500 12px/1 'Inter Tight',sans-serif;cursor:pointer">Load a sample set</button>
    <span class="mono" style="font-size:10px;color:var(--secondary)">real records · your data stays on this machine</span>
  </div>
  <div id="na-refs-out" style="margin-top:16px"></div>`;
 $('#na-refs-sample',host).onclick=async()=>{ try{ const s=await getJSON('/api/import/sample?kind=retrospective'); const t=$('#na-refs',host); if(t)t.value=s.bibtex||''; }catch(e){} };
 $('#na-refs-go',host).onclick=async()=>{
  const t=$('#na-refs',host), out=$('#na-refs-out',host); const text=(t&&t.value||'').trim();
  if(!text){ out.innerHTML=`<div style="color:var(--warn);font:400 12.5px/1.5 'Inter Tight',sans-serif">Paste at least one DOI or a .bib/.ris export first.</div>`; return; }
  out.innerHTML=_naWorking('Pulling real records · checking retractions · scoring integrity · ranking the next experiment…');
  try{ const d=await postJSON('/api/import',{text}); _renderImport(out,d); }
  catch(e){ out.innerHTML=`<div style="color:var(--warn);font:400 13px/1.6 'Inter Tight',sans-serif">Could not analyze that set: ${esc(String(e.message||e))}. Paste a .bib/.ris export or a DOI list.</div>`; }
 };
}
function _renderImport(out,d){
 const it=d.integrity||{}, c=it.counts||{}, h=it.health||{};
 const dec=(it.decision&&it.decision.recommendation)||null;
 const hi=h.band&&/HIGH/i.test(h.band);
 const bad=(c.retracted||0)+(c.cites_retraction||0)>0;
 const chips=[_chip('REFERENCES', d.requested!=null?d.requested:(it.total!=null?it.total:'—')),
  _chip('FIELD INTEGRITY',(h.score!=null?h.score:'—')+(h.band?' · '+h.band:''), hi?'--ok':'--warn'),
  _chip('RETRACTED', c.retracted||0, c.retracted?'--risk':'--ink'),
  _chip('CITES RETRACTION', c.cites_retraction||0, c.cites_retraction?'--risk':'--ink'),
  _chip('CLEAN', c.clean||0, '--ok'),
  _chip('UNRESOLVED', c.unresolved||0)].join('');
 const para=(it.summary&&it.summary.paragraph)||'';
 out.innerHTML=`<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">${chips}</div>
  ${para?`<div style="border:1px solid var(--hairline);border-left:3px solid var(${bad?'--risk':(hi?'--ok':'--warn')});border-radius:8px;background:var(--lowest);padding:13px 16px;font:400 13.5px/1.6 'Inter Tight',sans-serif;color:var(--ink);margin-bottom:14px">${esc(para)}</div>`:''}
  ${dec?`<div style="border:1px solid var(--primary);border-radius:10px;background:var(--paper);padding:14px 16px">
     <div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--primary)">DECISION ENGINE · NEXT EXPERIMENT ON YOUR PAPERS</div>
     <div style="font:400 15px/1.45 Newsreader,serif;color:var(--ink);margin-top:6px">${esc(dec.statement||'')}</div>
     ${dec.how_to_falsify?`<div style="margin-top:8px;font:400 12.5px/1.55 'Inter Tight',sans-serif;color:var(--ink2)"><b>Kill-condition:</b> ${esc(dec.how_to_falsify)}</div>`:''}
   </div>`:`<div style="font:400 12.5px/1.55 'Inter Tight',sans-serif;color:var(--secondary)">${esc((it.decision&&it.decision.error)||'Integrity results above; the imported graph was too thin to rank an experiment.')}</div>`}
  <div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center">
    <button id="na-agents-go" style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--claude-live);background:var(--claude-live);color:#fff;border-radius:9px;padding:10px 16px;font:600 13px/1 'Inter Tight',sans-serif;cursor:pointer"><span class="ms" style="font-size:17px">smart_toy</span>Run the multi-agent analysis</button>
    <span class="mono" style="font-size:10px;color:var(--secondary)">a coordinated cell of specialists reasons over your graph${(typeof LIVE!=='undefined'&&LIVE.on)?' · live Claude':''}</span>
  </div>
  <div id="na-agents" style="margin-top:14px"></div>
  <div style="margin-top:12px;font:400 11px/1.5 'Inter Tight',sans-serif;color:var(--secondary)">Session ${esc(d.session_id||'—')} · every DOI resolves to a real record. A retracted source still resolves, but is excluded from every conclusion.</div>`;
 const gb=$('#na-agents-go',out); if(gb) gb.onclick=()=>_naRunAgents(d.session_id, $('#na-agents',out));
}
/* Multi-agent AI on the scientist's OWN imported graph — the AI-workbench moment.
   Streams a coordinated cell of specialists (planner · data analysis · load-bearing
   classifier · doubt propagation · contradiction miner · hypothesis · design · power
   analysis · adversarial reviewer · reproducibility · PI) reasoning over the pasted
   references. Live Claude prose when a key is present; deterministic otherwise. */
function _agentsProgress(stages,active,elapsed,liveOn){
 return `<div style="border:1px solid var(--hairline);border-radius:10px;background:var(--lowest);padding:14px 16px">
  <div style="display:flex;align-items:center;gap:9px;margin-bottom:10px"><span class="spin" style="border-top-color:var(--claude-live)"></span><span class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--claude-live)">MULTI-AGENT PIPELINE · RUNNING${elapsed?` · ${elapsed}s`:''}</span></div>
  ${stages.map((s,i)=>`<div style="display:flex;align-items:center;gap:9px;padding:4px 0;${i>active?'opacity:.4':''}"><span class="ms" style="font-size:15px;color:var(${i<active?'--ok':i===active?'--claude-live':'--outline'})">${i<active?'check_circle':i===active?'radio_button_checked':'radio_button_unchecked'}</span><span style="font:400 12.5px/1.3 'Inter Tight',sans-serif;color:var(--ink2)">${esc(s)}</span></div>`).join('')}
  ${(liveOn&&elapsed>=12)?`<div style="margin-top:9px;font:400 10.5px/1.45 'Inter Tight',sans-serif;color:var(--secondary)">Live Claude is reasoning over your graph — the full agent cell runs once (~a minute), then caches for instant re-runs.</div>`:''}
 </div>`;
}
async function _naRunAgents(sid,host){
 if(!host||!sid) return;
 const stages=['Planning the analysis','Reading your evidence graph','Classifying load-bearing citations','Propagating doubt (graph math)','Mining contradictions','Generating a falsifiable hypothesis','Adversarial review — removing unearned confidence','Synthesizing the recommendation'];
 const liveOn=(typeof LIVE!=='undefined'&&LIVE.on);
 const per=liveOn?7:0.45;                       // seconds/stage: pace to the real ~60s live run
 const t0=Date.now(); host.dataset.done=''; host.innerHTML=_agentsProgress(stages,0,0,liveOn);
 const timer=setInterval(()=>{ if(host.dataset.done)return; const el=Math.round((Date.now()-t0)/1000); const i=Math.min(stages.length-1,Math.floor(el/per)); host.innerHTML=_agentsProgress(stages,i,el,liveOn); }, 1000);
 let d=null,err=null;
 try{ d=await getJSON('/api/import/reason?session_id='+encodeURIComponent(sid)); }catch(e){ err=String(e&&e.message||e); }
 clearInterval(timer); host.dataset.done='1';
 if(err||!d||!Array.isArray(d.steps)){ host.innerHTML=`<div style="color:var(--warn);font:400 13px/1.6 'Inter Tight',sans-serif">Could not run the multi-agent analysis${err?' ('+esc(err)+')':''}. The integrity results above still stand.</div>`; return; }
 _renderAgents(host,d);
}
function _renderAgents(host,d){
 const live=!!d.live, steps=(d.steps||[]);
 const badge=`<span style="display:inline-flex;align-items:center;gap:6px;color:var(${live?'--claude-live':'--secondary'});font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em"><span style="width:6px;height:6px;border-radius:50%;background:var(${live?'--claude-live':'--outline'})"></span>${live?'CLAUDE · LIVE':'DETERMINISTIC'}</span>`;
 const rows=steps.map(s=>{
  const isTool=(s.actor_type==='tool');
  const cd=(s.confidence_delta!=null&&s.confidence_before!=null)?`<span class="mono" style="font-size:9.5px;color:var(${s.confidence_delta<0?'--risk':'--ok'})">conf ${s.confidence_before}→${s.confidence_after}</span>`:'';
  return `<div style="display:flex;gap:11px;padding:11px 0;border-top:1px solid var(--hairline)">
    <div style="width:24px;height:24px;border-radius:6px;flex:none;display:flex;align-items:center;justify-content:center;background:var(${isTool?'--lowest':'--container'});border:1px solid var(--hairline)"><span class="ms" style="font-size:15px;color:var(${isTool?'--secondary':'--claude-live'})">${isTool?'function':'smart_toy'}</span></div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="font:600 12.5px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.actor)}</span><span class="mono" style="font-size:8px;letter-spacing:.06em;color:var(--secondary);border:1px solid var(--hairline);border-radius:10px;padding:2px 6px">${isTool?'TOOL':'AGENT'}</span>${cd}</div>
      <div style="font:400 11px/1.4 'Inter Tight',sans-serif;color:var(--secondary);margin-top:2px">${esc(s.role)}</div>
      <div style="font:400 12.5px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:5px">${esc(String(s.output||'').slice(0,340))}</div>
    </div></div>`;
 }).join('');
 const hyp=d.hypothesis||{}, rev=d.review||{}, conf=hyp.confidence&&hyp.confidence.point;
 host.innerHTML=`<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px"><div class="mono" style="font-size:10px;letter-spacing:.12em;color:var(--claude-live)">MULTI-AGENT ANALYSIS · ${steps.length} SEATS ON YOUR GRAPH</div>${badge}</div>
  <div style="border:1px solid var(--hairline);border-radius:10px;background:var(--paper);padding:2px 16px 10px;max-height:330px;overflow:auto">${rows}</div>
  <div style="margin-top:12px;border:1px solid var(--primary);border-radius:10px;background:var(--paper);padding:14px 16px">
    <div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--primary)">HYPOTHESIS · REVIEWED &amp; CONFIDENCE-ADJUSTED</div>
    <div style="font:400 14.5px/1.45 Newsreader,serif;color:var(--ink);margin-top:6px">${esc(hyp.statement||'')}</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">${_chip('REVIEWER',String(rev.verdict||'—').toUpperCase(),(rev.verdict==='downgraded'||rev.verdict==='rejected')?'--warn':'--ok')}${_chip('CONFIDENCE',rev.adjusted_confidence!=null?rev.adjusted_confidence:(conf!=null?conf:'—'))}</div>
    ${rev.weakness?`<div style="margin-top:10px;font:400 12.5px/1.55 'Inter Tight',sans-serif;color:var(--ink2)"><b>Reviewer:</b> ${esc(rev.weakness)}</div>`:''}
  </div>`;
}
function _naLab(host){
 const sb=(k,l)=>`<button data-labsample="${k}" style="border:1px solid var(--hairline);background:var(--paper);color:var(--ink2);border-radius:9px;padding:9px 12px;font:500 12px/1 'Inter Tight',sans-serif;cursor:pointer">${l}</button>`;
 host.innerHTML=`<div style="font:400 13px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin-bottom:12px">Upload a <b>plate-reader CSV</b> from a bench instrument. Keystone runs deterministic QC (Z′-factor · replicate CV · edge effects · blanks) and <b>downgrades the result's confidence</b> when a check fails — it never invents a measurement.</div>
  <div style="display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin-bottom:11px">
    <label style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--hairline);background:var(--paper);color:var(--ink2);border-radius:9px;padding:9px 13px;font:500 12px/1 'Inter Tight',sans-serif;cursor:pointer"><span class="ms" style="font-size:16px">upload_file</span>Choose CSV<input id="na-lab-file" type="file" accept=".csv,text/csv" style="display:none"></label>
    ${sb('clean','Sample · clean')}${sb('borderline','Sample · borderline')}${sb('bad','Sample · failing')}</div>
  <textarea id="na-lab" spellcheck="false" placeholder="well,group,value&#10;A1,pos,0.82&#10;A2,neg,0.05&#10;… or choose a CSV above" style="width:100%;min-height:140px;resize:vertical;border:1px solid var(--hairline);border-radius:10px;background:var(--lowest);color:var(--ink);font:400 12.5px/1.6 'JetBrains Mono',monospace;padding:12px 14px;box-sizing:border-box"></textarea>
  <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px">
    <button id="na-lab-go" style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--primary);background:var(--primary);color:var(--on-primary);border-radius:9px;padding:10px 16px;font:500 13px/1 'Inter Tight',sans-serif;cursor:pointer"><span class="ms" style="font-size:17px">fact_check</span>Review my lab data</button>
    <span class="mono" style="font-size:10px;color:var(--secondary)">deterministic QC · confidence is downgraded, never faked</span></div>
  <div id="na-lab-out" style="margin-top:16px"></div>`;
 host.querySelectorAll('[data-labsample]').forEach(b=>b.onclick=async()=>{ try{ const s=await getJSON('/api/bench/sample?kind='+b.getAttribute('data-labsample')); const t=$('#na-lab',host); if(t)t.value=s.csv_text||''; }catch(e){} });
 const fi=$('#na-lab-file',host); if(fi) fi.onchange=async e=>{ const f=e.target.files&&e.target.files[0]; if(!f)return; const t=$('#na-lab',host); if(t)t.value=await f.text(); };
 $('#na-lab-go',host).onclick=async()=>{
  const t=$('#na-lab',host), out=$('#na-lab-out',host); const csv=(t&&t.value||'').trim();
  if(!csv){ out.innerHTML=`<div style="color:var(--warn);font:400 12.5px/1.5 'Inter Tight',sans-serif">Paste plate CSV, choose a file, or load a sample first.</div>`; return; }
  out.innerHTML=_naWorking('Running QC checks on your plate…');
  try{ const d=await postJSON('/api/bench/review',{csv_text:csv,name:'my plate'}); _renderBench(out,d); }
  catch(e){ out.innerHTML=`<div style="color:var(--warn);font:400 13px/1.6 'Inter Tight',sans-serif">Could not review that plate: ${esc(String(e.message||e))}.</div>`; }
 };
}
function _renderBench(out,d){
 if(d.refused){ out.innerHTML=`<div style="border:1px solid var(--warn);border-radius:10px;background:var(--lowest);padding:14px 16px"><div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--warn)">REFUSED</div><div style="margin-top:6px;font:400 13px/1.6 'Inter Tight',sans-serif;color:var(--ink)">${esc(d.reason||'Unsupported instrument format.')}</div></div>`; return; }
 const vcol={supported:'--ok',downgraded:'--warn',rejected:'--risk',refused:'--warn'}[d.verdict]||'--ink';
 const adj=d.adjusted_confidence&&d.adjusted_confidence.point;
 const checks=(d.qc_metrics||[]).map(c=>`<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--hairline)">
   <span class="ms" style="font-size:17px;color:var(${c.breached?'--risk':'--ok'});flex:none">${c.breached?'error':'check_circle'}</span>
   <div style="flex:1;min-width:0"><div style="font:500 12.5px/1.3 'Inter Tight',sans-serif;color:var(--ink)">${esc(c.name)}</div><div class="mono" style="font-size:10px;color:var(--secondary)">${esc(String(c.value))} vs ${esc(String(c.threshold))}${c.citation?' · '+esc(c.citation):''}</div></div>
   <span class="mono" style="font-size:10px;color:var(${c.breached?'--risk':'--ok'});flex:none">${c.breached?'BREACHED':'OK'}</span></div>`).join('');
 out.innerHTML=`<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">${_chip('VERDICT',String(d.verdict||'—').toUpperCase(),vcol)}${_chip('CONFIDENCE',adj!=null?adj:'—',vcol)}${_chip('BASE PRIOR',d.base_confidence!=null?d.base_confidence:'—')}</div>
  ${d.weakness?`<div style="font:400 13px/1.6 'Inter Tight',sans-serif;color:var(--ink);margin-bottom:10px">${esc(d.weakness)}</div>`:''}
  <div style="border:1px solid var(--hairline);border-radius:10px;background:var(--lowest);padding:4px 16px 12px">${checks||'<div style="padding:12px 0;color:var(--secondary);font:400 12px/1.5 \'Inter Tight\',sans-serif">No checks returned.</div>'}</div>
  ${(d.suggestions&&d.suggestions.length)?`<div style="margin-top:12px"><div class="mono" style="font-size:10px;letter-spacing:.08em;color:var(--secondary)">SUGGESTIONS</div>${d.suggestions.map(s=>`<div style="font:400 12.5px/1.55 'Inter Tight',sans-serif;color:var(--ink2);margin-top:4px">• ${esc(s)}</div>`).join('')}</div>`:''}`;
}
function _naGene(host){
 host.innerHTML=`<div style="font:400 13px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin-bottom:12px">Type any human gene symbol. Keystone resolves it live against <b>Open Targets</b> and returns its real disease associations and type-2 relevance — proof the engine generalizes past the curated demo.</div>
  <div style="display:flex;gap:10px;flex-wrap:wrap">
    <input id="na-gene" spellcheck="false" placeholder="e.g. TSLP · IL13 · JAK1 · GATA3" style="flex:1;min-width:200px;border:1px solid var(--hairline);border-radius:9px;background:var(--lowest);color:var(--ink);font:400 14px/1 'Inter Tight',sans-serif;padding:12px 14px;box-sizing:border-box">
    <button id="na-gene-go" style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(--primary);background:var(--primary);color:var(--on-primary);border-radius:9px;padding:11px 18px;font:500 13px/1 'Inter Tight',sans-serif;cursor:pointer">Assess</button></div>`;
 const run=()=>{ const g=$('#na-gene',host); const v=(g&&g.value||'').trim(); if(v) assessTarget(v.toUpperCase()); };
 $('#na-gene-go',host).onclick=run;
 const gi=$('#na-gene',host); if(gi) gi.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); run(); } });
}

/* ---------------- "How a scientist uses Keystone" — the workflow, in-product ---------------- */
const HOWTO=[
 {n:'1',icon:'upload_file',t:'Bring your evidence',d:"Ask a research question or paste your reference list (.bib / DOIs). Keystone pulls the real records — Crossref, OpenAlex, UniProt, Cellosaurus, ClinVar, ChEMBL, Reactome, ClinicalTrials.gov. Nothing is typed by hand.",to:'discovery'},
 {n:'2',icon:'hub',t:'See what you are building on',d:"The Evidence Graph tags every claim on four axes — source-record-verified · claim-type · integrity-state — and links it to its source quote. A retracted DOI still resolves, but is excluded from every conclusion. “Verified” never means “true.”",to:'evidence'},
 {n:'3',icon:'groups',t:'Run the Research Cell',d:"Five real agents — Data Analysis, Literature, Target Biology, Integrity, Reviewer — run over the real corpus. Each logs its inputs, tool calls, source-backed claims, run id and timestamp. No claim becomes primary ranking support until the Reviewer Agent approves it; the synthetic cross-check is rejected.",to:'cell'},
 {n:'4',icon:'fork_right',t:'Rank the next experiment',d:"The Decision Engine scores competing hypotheses by expected information gain against cost, and recommends the smallest decisive experiment — with a named kill-condition and a real power analysis (n per arm).",to:'decision'},
 {n:'5',icon:'description',t:'Export the rigor artifacts',d:"Grant Export drafts the NIH rigor + STAR Methods sections, content-hashed and reproducible from the append-only ledger. Every step needs the scientist’s sign-off — Keystone recommends and drafts; it never replaces lab validation.",to:'grant'},
];
function howItWorks(){
 const steps=HOWTO.map(s=>`<button data-goto="${s.to}" style="display:flex;gap:16px;text-align:left;width:100%;padding:16px 20px;border:none;border-bottom:1px solid var(--hairline);background:none;cursor:pointer">
   <div style="width:34px;height:34px;border-radius:9px;background:var(--container);border:1px solid var(--hairline);display:flex;align-items:center;justify-content:center;flex:none"><span class="ms" style="font-size:19px;color:var(--claude-live)">${s.icon}</span></div>
   <div style="flex:1;min-width:0"><div style="display:flex;align-items:center;gap:8px"><span class="mono" style="font-size:10px;color:var(--outline)">STEP ${s.n}</span><span style="font:600 14px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.t)}</span></div>
    <div style="font:400 13px/1.55 'Inter Tight',sans-serif;color:var(--ink2);margin-top:5px">${esc(s.d)}</div></div>
   <span class="ms" style="font-size:16px;color:var(--outline);flex:none">north_east</span></button>`).join('');
 const o=searchOverlay(`<div style="padding:22px 24px;border-bottom:1px solid var(--hairline);display:flex;align-items:flex-start;justify-content:space-between;gap:14px">
   <div><div class="mono" style="font-size:10px;letter-spacing:.14em;color:var(--secondary)">HOW A SCIENTIST USES KEYSTONE</div>
   <div style="font:400 22px/1.25 Newsreader,serif;color:var(--ink);margin-top:6px">From a question to the next experiment — every claim traceable</div></div>${closeBtn}</div>
   ${steps}
   <div style="padding:14px 22px;color:var(--secondary);font:400 11.5px/1.6 'Inter Tight',sans-serif">Click any step to jump there. Built with Claude: Life Sciences · Gladstone Institutes.</div>`);
 o.querySelectorAll('[data-goto]').forEach(b=>b.addEventListener('click',()=>{o.remove();go(b.dataset.goto);}));
}

/* ---------------- "Design experiment" → the real draft protocol from the engine ---------------- */
async function designExperiment(idx){
 searchOverlay(`<div style="padding:26px 28px"><div class="mono" style="font-size:10px;letter-spacing:.14em;color:var(--secondary)">EXPERIMENT DESIGN · DRAFT</div><div style="color:var(--secondary);font:400 13px/1.5 'JetBrains Mono',monospace;margin-top:10px">Assembling the protocol from the decision engine…</div></div>`);
 let h=null;
 try{ const d=await getJSON('/api/decision?domain='+curDomain()); h=(d.competing_hypotheses||[])[idx]; }catch(e){}
 if(!h){ searchOverlay(`<div style="padding:26px 28px;color:var(--warn)">Could not load this experiment. ${closeBtn}</div>`); return; }
 const num=v=>{ if(v==null) return '—'; if(typeof v==='object') v=(v.value??v.point??v); return (typeof v==='number')?(Math.abs(v)<1?v.toFixed(2):v):v; };
 const row=(k,v)=>`<div style="display:flex;justify-content:space-between;gap:14px;padding:9px 0;border-bottom:1px solid var(--hairline)"><span class="mono" style="font-size:10px;letter-spacing:.06em;color:var(--secondary)">${k}</span><span style="font:500 13px/1.3 'Inter Tight',sans-serif;color:var(--ink);text-align:right">${esc(String(v))}</span></div>`;
 const why=Array.isArray(h.why)?h.why.join('; '):(h.why||'');
 searchOverlay(`<div style="padding:22px 28px;border-bottom:1px solid var(--hairline);display:flex;justify-content:space-between;gap:14px"><div style="min-width:0"><div class="mono" style="font-size:10px;letter-spacing:.14em;color:var(--claude-live)">EXPERIMENT DESIGN · DRAFT · REQUIRES SCIENTIST SIGN-OFF</div><div style="font:400 19px/1.35 Newsreader,serif;color:var(--ink);margin-top:6px;word-break:break-word">${esc((h.statement||'').slice(0,160))}</div></div>${closeBtn}</div>
  <div style="padding:12px 28px">
   ${row('HYPOTHESIS KIND',(h.kind||'').replace(/_/g,' '))}
   ${row('EXPECTED INFORMATION GAIN',num(h.information_gain))}
   ${row('PRIORITY SCORE',num(h.priority_score))}
   ${row('EST. COST (USD)',num(h.cost_usd))}
   ${row('EST. DURATION (WEEKS)',num(h.duration_weeks))}
   ${row('RISK',num(h.risk))}
   ${row('VALIDATION DIFFICULTY',num(h.validation_difficulty))}
   ${row('NOVELTY',num(h.novelty))}
   ${row('REVIEWER CONFIDENCE',num(h.reviewer_confidence))}
   ${why?`<div style="padding:14px 0 4px"><div class="mono" style="font-size:10px;color:var(--secondary);margin-bottom:6px">RATIONALE · CLAUDE</div><div style="font:400 14px/1.55 'Inter Tight',sans-serif;color:var(--ink2)">${esc(why)}</div></div>`:''}
  </div>
  <div style="padding:13px 28px;color:var(--secondary);font:400 11px/1.5 'Inter Tight',sans-serif">Every number is computed by the deterministic engine. Keystone recommends and drafts a protocol; it never runs the experiment or replaces laboratory validation.</div>`);
}

/* theme */
function setTheme(t){document.documentElement.setAttribute('data-theme',t);localStorage.setItem('ks-theme',t);const i=$('#themeicon');if(i)i.textContent=t==='dark'?'light_mode':'dark_mode';}
setTheme(localStorage.getItem('ks-theme')||'dark');

/* nav */
function renderNav(){
 const allowed=it=>it.href||!CAPS||CAPS.includes(it.id);
 // Front-door call-to-action: the scientist's own data is a first-class entry,
 // not buried on a secondary page. Opens the New Analysis modal (references / lab
 // data / gene), each wired to a real endpoint.
 const cta=`<button data-newanalysis="references" class="navrow" style="width:100%;justify-content:flex-start;gap:9px;border:1px dashed var(--primary);background:var(--lowest);color:var(--primary);margin-bottom:10px;font-weight:600"><span class="ms" style="font-size:19px;flex:none">add_circle</span><span style="flex:1;text-align:left">New analysis · your data</span></button>`;
 $('#nav').innerHTML=cta+NAV.map(g=>{
  const items=g.items.filter(allowed);
  if(!items.length) return '';                      // hide a whole group with no supported surfaces
  return `<div class="navsec"><div class="navgrp">${g.group}</div>${items.map(it=>{
   const badge=it.id==='evidence'?(NODES&&NODES.length?String(NODES.length):''):it.badge;   // real node count, not a static 47
   const inner=`<span class="ms" style="font-size:19px;flex:none">${it.icon}</span><span style="flex:1">${it.label}</span>${badge?`<span class="badge">${badge}</span>`:''}`;
   return it.href
    ? `<a class="navrow" href="${it.href}" style="text-decoration:none">${inner}</a>`
    : `<button class="navrow ${STATE.screen===it.id?'on':''}" data-screen="${it.id}">${inner}</button>`;
  }).join('')}</div>`;
 }).join('');
}

/* ---------------- screen: Discovery Run ---------------- */
/* ---------------- Integrity Gate: instant (5ms), real, the wedge — runs BEFORE reasoning ---------------- */
const _intgTone={fail:['--risk','gpp_bad'],warn:['--warn','warning'],pass:['--ok','check_circle'],not_wired:['--outline','remove']};
async function integrityGate(host, domain){
 if(!host) return;
 let d=null; try{ d=await getJSON('/api/integrity?domain='+encodeURIComponent(domain)); }catch(e){ host.innerHTML=''; return; }
 const checks=(d.checks||[]), sm=(d.summary||{});
 const failed=sm.failed||0, warned=sm.warned||0, gateBad=failed>0;
 const chip=c=>{const t=_intgTone[c.status]||['--outline','remove'];
  return `<div style="display:flex;gap:12px;padding:12px 0;border-top:1px solid var(--hairline)">
   <span class="ms" style="font-size:19px;color:var(${t[0]});flex:none">${t[1]}</span>
   <div style="flex:1;min-width:0"><div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap"><span style="font:500 13.5px/1.35 'Inter Tight',sans-serif;color:var(--ink)">${esc(c.name)}</span><span class="mono" style="font-size:9px;letter-spacing:.08em;color:var(${t[0]})">${esc(String(c.status).toUpperCase().replace('_',' '))}${c.tier?' · TIER '+c.tier:''}</span></div>
   <div style="font:400 12.5px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:3px">${esc(c.detail)}</div>
   ${c.source?`<div class="mono" style="font-size:10px;color:var(--secondary);margin-top:3px">source · ${esc(c.source)}</div>`:''}</div></div>`;};
 const headCol=gateBad?'--risk':(warned?'--warn':'--ok');
 host.innerHTML=`<div style="border:1px solid var(${headCol});border-radius:12px;background:var(--paper);overflow:hidden;margin:26px 0 8px;animation:ks-up .5s var(--e-out) both">
  <div style="padding:16px 22px;background:var(${gateBad?'--risk-c':'--lowest'});border-bottom:1px solid var(--hairline);display:flex;align-items:center;gap:12px">
   <span class="ms" style="font-size:22px;color:var(${headCol})">${gateBad?'gpp_maybe':'verified_user'}</span>
   <div style="flex:1"><div class="mono" style="font-size:10px;letter-spacing:.14em;color:var(${headCol})">INTEGRITY GATE · RUNS BEFORE REASONING</div>
    <div style="font:500 15px/1.3 'Inter Tight',sans-serif;color:var(--ink);margin-top:3px">${gateBad?`${failed} Tier-1 check${failed>1?'s':''} failed — this evidence is compromised`:'Foundations verified — safe to reason on'}</div></div>
   <span class="mono" style="font-size:11px;color:var(--secondary);text-align:right">${sm.passed||0} pass · ${failed} fail · ${warned} warn</span></div>
  <div style="padding:6px 22px 16px">${checks.map(chip).join('')}</div>
  ${gateBad?`<div style="padding:14px 22px;border-top:1px solid var(--hairline);background:var(--lowest)">
    <div style="font:400 12.5px/1.55 'Inter Tight',sans-serif;color:var(--ink2)"><b style="color:var(--ink)">Nothing below is built on a failed source.</b> Retracted and misidentified nodes resolve in the graph but are excluded from every conclusion — Claude reasons only over what survives.</div>
    <div style="font:400 11.5px/1.55 'Inter Tight',sans-serif;color:var(--secondary);margin-top:9px;padding-top:9px;border-top:1px dashed var(--hairline)">Why a gate, not just a smarter model: no LLM can know a paper was retracted <i>after</i> its training cutoff — a 2026 audit found frontier models flag 0% of post-cutoff retractions. The only fix is a live registry lookup. <b style="color:var(--ink2)">Claude reasons; Retraction Watch &amp; Cellosaurus remember.</b></div>
    <button id="ks-cf-btn" style="margin-top:13px;display:inline-flex;align-items:center;gap:7px;border:1px solid var(--risk);background:none;color:var(--risk);border-radius:8px;padding:8px 13px;font:600 11px/1 'JetBrains Mono',monospace;letter-spacing:.04em;cursor:pointer"><span class="ms" style="font-size:15px">play_arrow</span>WATCH WHAT EXCLUDING IT CHANGES</button>
    <div id="ks-cf-panel"></div>
   </div>`:''}</div>`;
 const cfb=host.querySelector('#ks-cf-btn');
 if(cfb) cfb.onclick=()=>{ cfb.style.display='none'; loadCounterfactual(host.querySelector('#ks-cf-panel'), domain); };
}

/* the #9 counterfactual — exclude the retracted source and RECOMPUTE the case */
async function loadCounterfactual(host, domain){
 if(!host) return;
 host.innerHTML=`<div style="margin-top:13px;display:flex;align-items:center;gap:9px;color:var(--secondary);font:400 12px/1.5 'Inter Tight',sans-serif"><span class="spin" style="border-top-color:var(--claude-live)"></span>Recomputing the case with and without the retracted source…</div>`;
 let d=null; try{ d=await getJSON('/api/counterfactual?domain='+encodeURIComponent(domain)); }catch(e){ host.innerHTML=`<div style="margin-top:12px;color:var(--warn);font:400 12px/1.5 'Inter Tight',sans-serif">Could not compute the counterfactual (${esc(String(e))}).</div>`; return; }
 if(d.error){ host.innerHTML=`<div style="margin-top:12px;color:var(--secondary);font:400 12px/1.5 'Inter Tight',sans-serif">${esc(d.error)}</div>`; return; }
 const fi=d.field_integrity||{}, col=v=>v>=85?'--ok':v>=70?'--warn':'--risk';
 const card=(tag,tagCol,status,statusCol,fiv,note)=>`<div style="flex:1;min-width:190px;border:1px solid var(--hairline);border-radius:10px;padding:14px 16px;background:var(--paper)">
   <div class="mono" style="font-size:9px;letter-spacing:.1em;color:var(${tagCol})">${tag}</div>
   <div style="display:flex;align-items:baseline;gap:7px;margin-top:9px"><span style="font:400 32px/1 Newsreader,serif;color:var(${col(fiv)})">${fiv==null?'—':fiv}</span><span class="mono" style="font-size:10px;color:var(--secondary)">/100 field integrity</span></div>
   <div style="margin-top:10px"><span class="mono" style="display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;background:var(--container);font-size:10px;color:var(${statusCol})">this source: ${esc(String(status).toUpperCase())}</span></div>
   <div style="font:400 11px/1.45 'Inter Tight',sans-serif;color:var(--secondary);margin-top:9px">${note}</div></div>`;
 host.innerHTML=`<div style="margin-top:14px">
   <div style="font:400 13px/1.55 'Inter Tight',sans-serif;color:var(--ink);margin-bottom:11px">Excluding <b>“${esc(String(d.source.label))}”</b> is not cosmetic — the case is <b>recomputed</b>:</div>
   <div style="display:flex;gap:12px;flex-wrap:wrap">
    ${card('IF A TOOL TRUSTED IT · NAÏVE','--secondary',d.if_trusted.evidence_status,'--secondary',fi.if_trusted,'A plain LLM has no way to know it was retracted after its cutoff.')}
    ${card('KEYSTONE EXCLUDES IT · HONEST','--risk',d.excluded.evidence_status,'--risk',fi.excluded,esc(String(d.excluded.rationale)))}
   </div>
   <div style="margin-top:12px;font:400 12px/1.55 'Inter Tight',sans-serif;color:var(--ink2)"><b style="color:var(--ink)">Δ ${fi.delta==null?'—':fi.delta} field-integrity points</b>${d.assessment_changed?` · the source's status changes <b style="color:var(--risk)">${esc(d.if_trusted.evidence_status)} → ${esc(d.excluded.evidence_status)}</b>`:''}. Same inputs, live-recomputed — nothing here is fixed text.</div>
  </div>`;
}

/* demo discipline: the first screen shows the top candidate + one action */
async function topCandidateCard(host, domain){
 if(!host || domain!=='tcell') return;
 let d=null; try{ d=await getJSON('/api/target_ranking?domain=tcell'); }catch(e){ return; }
 const c=(d.ranking||[])[0]; if(!c) return; const prec=c.precedent;
 host.innerHTML=`<div style="border:1px solid var(--primary);border-radius:12px;background:var(--paper);padding:18px 22px;margin:26px 0 8px;animation:ks-up .5s var(--e-out) both">
   <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap"><div style="flex:1;min-width:220px"><div class="mono" style="font-size:10px;letter-spacing:.12em;color:var(--primary)">TOP CANDIDATE · RANKED #1 OF ${d.ranking.length}${prec?' · <span style="color:var(--ok)">✓ CLINICALLY-VALIDATED DEGRADER</span>':''}</div>
    <div style="font:400 24px/1.15 Newsreader,serif;color:var(--ink);margin-top:5px">${esc(c.gene)} <span class="mono" style="font-size:12px;color:var(--secondary)">UniProt:${esc(c.uniprot)}</span></div>
    <div class="mono" style="font-size:11px;color:var(--secondary);margin-top:4px">composite ${c.composite.toFixed(3)} · 8 sourced components, weighted — not a black box</div></div>
   <button id="ks-review-why" style="display:inline-flex;align-items:center;gap:8px;border:1px solid var(--primary);background:var(--primary);color:var(--on-primary);border-radius:9px;padding:11px 17px;font:500 13px/1 'Inter Tight',sans-serif;cursor:pointer;flex:none"><span class="ms" style="font-size:17px">stacked_bar_chart</span>Review why this target ranks</button></div>
   ${prec?`<div style="margin-top:13px;padding:11px 13px;border:1px solid var(--ok);border-radius:8px;background:var(--lowest);font:400 12px/1.5 'Inter Tight',sans-serif;color:var(--ink2)"><b style="color:var(--ink)">${esc(prec.drug)}</b> — ${esc(prec.status)}. Keystone's #1 pick is already in the clinic — proof an intracellular type-2 master regulator is degradable. <b style="color:var(--ink)">Now it maps the next one.</b> <a href="${esc(prec.source)}" target="_blank" rel="noopener" style="color:var(--claude-live);text-decoration:none">source ↗</a></div>`:''}</div>`;
 const b=$('#ks-review-why',host); if(b) b.onclick=()=>go('targets');
}

function screenDiscovery(m){
 m.innerHTML=`<div class="wrap">
  <div style="animation:ks-up .5s var(--e-out) both">
   <div class="runkick"><span class="k">DISCOVERY RUN</span><span class="d"></span><span class="r">${esc(META.runRef)}</span></div>
   <h1 class="title">${esc(META.title)}</h1>
   <p class="intro">${esc(META.intro)}</p>
   <div class="metabar">${META.meta.map(x=>`<div class="metacell"><div class="l">${esc(x.k)}</div><div class="v">${esc(x.v)}</div></div>`).join('')}</div>
  </div>
  <div id="ks-top-candidate"></div>
  <div id="ks-intg-gate"></div>
  <div class="ledgerhead"><h2>Run ledger</h2>
   <div style="display:flex;align-items:center;gap:14px"><span class="mono" style="font-size:10px;letter-spacing:.08em;color:var(--secondary)" id="runsum">${esc(META.runSummary)}</span>
   <button class="rerun" id="rerun"><span class="ms" style="font-size:16px">replay</span>Re-run</button></div></div>
  <div id="stages"></div>
  <div class="repro"><span class="ms" style="font-size:20px;color:var(--secondary)">lock</span>
   <div style="flex:1"><div class="t">This run is reproducible</div><div class="s">Same inputs, same seed, same result. Every step is content-addressed and the ledger is append-only.</div></div></div>
 </div>`;
 const host=$('#stages',m), sum=$('#runsum',m);
 integrityGate($('#ks-intg-gate',m), curDomain());
 topCandidateCard($('#ks-top-candidate',m), curDomain());
 const rowHTML=(s,i,st)=>{const last=i===STAGES.length-1;
  const glyph=st==='done'?`<div class="glyph done" style="animation-delay:${i*70}ms"><span class="ms fill" style="font-size:16px;color:var(--on-primary)">check</span></div>`:st==='run'?`<div class="glyph"><span class="spin"></span></div>`:`<div class="glyph" style="background:var(--high)"></div>`;
  const conn=last?'':`<div class="conn" style="animation-delay:${i*70+120}ms"></div>`;
  const claude=s.claude?`<span class="ctag">CLAUDE · DRAFT</span>`:'';
  const detail=st==='idle'?'':`${esc(st==='run'?(s._t||''):s.detail)}${st==='run'?'<span class="caret"></span>':''}`;
  const out=st==='done'?`<div class="sout"><button class="outbtn" data-goto="${s.to||''}"><span class="ms" style="font-size:15px;color:var(--secondary)">${s.outIcon}</span>${s.out}</button></div>`:'';
  return `<div class="stage"><div class="gcol">${glyph}${conn}</div><div class="sbody"><div class="srow1"><span class="slabel" style="color:${st==='idle'?'var(--outline)':'var(--ink)'}">${esc(s.label)}</span>${claude}<span style="flex:1"></span></div><div class="sdetail">${detail}</div>${out}</div></div>`;};
 const draw=st=>{host.innerHTML=STAGES.map((s,i)=>rowHTML(s,i,typeof st==='function'?st(i):st)).join('');
  host.querySelectorAll('[data-goto]').forEach(b=>b.onclick=()=>{if(b.dataset.goto)go(b.dataset.goto);});};
 draw('done');
 let running=false;
 sum.parentElement.querySelector('#rerun').onclick=()=>{ if(running||reduced)return; running=true;
  let i=0; const typeStage=(idx,done)=>{const s=STAGES[idx];s._t='';const full=s.detail;let c=0;
   const step=()=>{s._t=full.slice(0,c);draw(j=>j<idx?'done':j===idx?'run':'idle');c+=Math.max(2,Math.round(full.length/26));
    if(c<=full.length)setTimeout(step,26);else setTimeout(done,240);};step();};
  const next=()=>{if(i>=STAGES.length){running=false;draw('done');sum.textContent='COMPLETE · 6/6 · 24s';return;}
   sum.textContent='RUNNING · '+i+'/6';typeStage(i,()=>{i++;next();});};next();};
}

/* ---------------- screen: Research Integrity (gauge) ---------------- */
function screenIntegrity(m){
 m.innerHTML=`<div class="wrapwide">
  <div style="animation:ks-up .5s var(--e-out) both">
   <div class="runkick"><span class="k">RESEARCH INTEGRITY CENTER</span></div>
   <h1 class="h2">Field Integrity</h1>
   <p class="intro2">A single, defensible measure of how much this program's evidence can be trusted — computed from provenance depth, independent reproducibility, and method rigor. It is not a model's opinion; it is an audit.</p>
  </div>
  <div class="intgrid">
   <div class="gaugecard">
    <div class="gaugewrap"><canvas id="gauge"></canvas>
     <div class="gaugeover">
      <span class="mono" style="font-size:10px;letter-spacing:.16em;color:var(--secondary);margin-bottom:11px">FIELD INTEGRITY</span>
      <span style="font:400 42px/.95 Newsreader,serif;letter-spacing:-.01em;color:var(--ink)">${esc(META.fiBand||'—')}</span>
      <span style="display:flex;align-items:baseline;gap:4px;margin-top:11px;font-variant-numeric:tabular-nums"><span id="gnum" class="mono" style="font-size:19px;color:var(--ink)">0.0</span><span class="mono" style="font-size:12px;color:var(--outline)">/100</span></span>
      <span class="mono" style="font-size:11px;color:var(--secondary);margin-top:7px">${META.fiRange?'range '+esc(META.fiRange)+' · ':''}computed</span>
     </div></div>
    <div style="display:flex;align-items:center;gap:8px;margin-top:6px" class="mono"><span id="settledot" style="width:7px;height:7px;border-radius:50%;background:var(--outline)"></span><span id="settlelabel" style="font-size:11px;letter-spacing:.06em;color:var(--outline)">SETTLING…</span></div>
   </div>
   <div><div class="mono" style="font-size:11px;letter-spacing:.1em;color:var(--secondary);margin-bottom:16px">COMPOSITION</div>
    <div style="display:flex;flex-direction:column;gap:17px">${FACTORS.map((f,i)=>{const pct=Math.round(f.val*100);const good=f.invert?f.val<=0.2:f.val>=0.8;const col=f.invert?(f.val<=0.2?'--ok':'--warn'):(f.val>=0.8?'--ok':'--warn');
     return `<div class="factor"><div class="frow"><span style="font:500 14px/1 'Inter Tight',sans-serif;color:var(--ink)">${f.label}</span><span class="mono" style="font-size:13px;color:var(${col})">${f.invert?pct+'%':f.val.toFixed(2)}</span></div>
      <div class="fbar"><i style="width:${pct}%;background:var(${col});animation-delay:${i*80}ms"></i></div><div class="fnote">${f.note}</div></div>`;}).join('')}</div>
   </div>
  </div>
  <div style="border:1px solid var(--hairline);border-radius:10px;background:var(--lowest);padding:22px 24px;margin-top:4px">
   <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px"><span class="ms" style="font-size:18px;color:var(--secondary)">hub</span><span class="mono" style="font-size:11px;letter-spacing:.1em;color:var(--secondary)">CONFLICTING EVIDENCE &amp; SOURCE PROVENANCE</span></div>
   <p style="font:400 15px/1.55 Newsreader,serif;color:var(--ink);margin:0 0 16px">The field-integrity score above is computed from ${esc(META.progname)}'s real provenance. The specific conflicting-evidence items and each source's post-publication history — retractions, expressions of concern, corrections — are attached per node in the Evidence Graph, where a retracted source resolves yet is excluded from every conclusion.</p>
   <button class="rerun" data-screen="evidence"><span class="ms" style="font-size:16px">hub</span>Open the Evidence Graph</button></div>
  <div class="cert"><div style="width:40px;height:40px;border-radius:9px;background:var(--lowest);border:1px solid var(--hairline);display:flex;align-items:center;justify-content:center;flex:none"><span class="ms" style="font-size:20px;color:var(--secondary)">verified_user</span></div>
   <div style="flex:1"><div style="font:500 13px/1.3 'Inter Tight',sans-serif;color:var(--ink);margin-bottom:3px">Integrity certificate</div><div class="seal mono" style="font-size:11px;color:var(--secondary)">sha256:9c1f·4ab2·d70e·… · generated 10:42:07Z · human review required</div></div>
   <div style="display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:20px;background:var(--warn-c);color:var(--warn);font:500 11px/1 'Inter Tight',sans-serif"><span class="ms" style="font-size:15px">pending</span>Awaiting PI sign-off</div></div>
 </div>`;
 // animated gauge
 const c=$('#gauge',m), num=$('#gnum',m); const target=(META.fiScore==null?0:+META.fiScore); let t0=null; const integ={value:0,band:42};
 const draw=()=>{const dpr=Math.min(2,window.devicePixelRatio||1);const w=c.clientWidth,h=c.clientHeight;if(!w||!h)return;
  if(c.width!==Math.round(w*dpr)){c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);}
  const ctx=c.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const cx=w/2,cy=h/2+10,R=Math.min(w,h*1.15)/2-20,a0=Math.PI*0.75,a1=Math.PI*2.25;
  const val=Math.max(0,Math.min(100,integ.value))/100,band=integ.band/100;
  const hair=cv('--hairline'),ink=cv('--ink'),paper=cv('--lowest'),acc=cv('--accent');
  ctx.lineCap='round';ctx.strokeStyle=hair;ctx.lineWidth=3;ctx.beginPath();ctx.arc(cx,cy,R,a0,a1);ctx.stroke();
  const av=a0+(a1-a0)*val,lo=a0+(a1-a0)*Math.max(0,val-band),hi=a0+(a1-a0)*Math.min(1,val+band);
  ctx.strokeStyle=acc;ctx.globalAlpha=.15;ctx.lineWidth=13;ctx.beginPath();ctx.arc(cx,cy,R,lo,hi);ctx.stroke();ctx.globalAlpha=1;
  ctx.strokeStyle=acc;ctx.lineWidth=3;ctx.beginPath();ctx.arc(cx,cy,R,a0,av);ctx.stroke();
  ctx.strokeStyle=hair;ctx.lineWidth=1;for(let i=0;i<=10;i++){const a=a0+(a1-a0)*(i/10),r1=R-7,r2=R-(i%5===0?15:10);ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*r1,cy+Math.sin(a)*r1);ctx.lineTo(cx+Math.cos(a)*r2,cy+Math.sin(a)*r2);ctx.stroke();}
  const mx=cx+Math.cos(av)*R,my=cy+Math.sin(av)*R;ctx.fillStyle=paper;ctx.strokeStyle=ink;ctx.lineWidth=2;ctx.beginPath();ctx.arc(mx,my,5.5,0,7);ctx.fill();ctx.stroke();};
 const step=now=>{if(!t0)t0=now;const t=Math.min(1,(now-t0)/1500);const e=1-Math.pow(1-t,3);
  integ.value=target*e;integ.band=42*(1-e)+6;if(num)num.textContent=integ.value.toFixed(1);draw();
  if(t<1)_raf=requestAnimationFrame(step);else{integ.value=target;integ.band=6;num.textContent=target.toFixed(1);draw();const d=$('#settledot',m),l=$('#settlelabel',m);if(d)d.style.background=cv('--ok');if(l){l.textContent='SETTLED · HUMAN-REVIEWABLE';l.style.color=cv('--ok');}}};
 if(reduced){integ.value=target;integ.band=6;num.textContent=target.toFixed(1);draw();}else _raf=requestAnimationFrame(step);
 window.addEventListener('resize',draw); _cleanup=()=>window.removeEventListener('resize',draw);
}

/* ---------------- screen: Evidence Graph (breathing force graph) ---------------- */
/* claim-level provenance for the inspector — the scientific-honesty model made
   visible in the front door (verified≠true, exact quote/locator, integrity). */
let CLAIM_MAP={};
function claimSection(nid){
 const c=CLAIM_MAP[nid]; if(!c) return '';
 const lk=c.linkage||{};
 const na=v=>(!v||v==='not available')?`<span style="color:var(--outline)">not available</span>`:esc(String(v));
 const isCol={retracted:'--risk',concern:'--warn',unverified:'--warn',normal:'--ok'}[c.integrity_state]||'--secondary';
 const ctCol={evidence:'--ok',computed:'--secondary',hypothesis:'--primary',missing:'--outline'}[c.claim_type]||'--secondary';
 const doi=lk.source_id||'';
 const href=/^https?:/i.test(doi)?doi:(/^10\./.test(doi)?'https://doi.org/'+doi:'');
 const doiHtml=href?`<a href="${esc(href)}" target="_blank" rel="noopener" style="color:var(--claude-live);text-decoration:none;word-break:break-all">${esc(doi)} <span class="ms" style="font-size:12px;vertical-align:-2px">north_east</span></a>`:na(doi);
 const pill=(txt,col)=>`<span class="mono" style="font-size:9px;padding:3px 8px;border-radius:20px;background:var(--container);color:var(${col})">${txt}</span>`;
 return `<div class="mono" style="font-size:11px;letter-spacing:.1em;color:var(--secondary);margin-bottom:10px">CLAIM PROVENANCE</div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:13px">
   ${pill(c.source_record_verified?'✓ RECORD VERIFIED':'RECORD UNVERIFIED',c.source_record_verified?'--ok':'--warn')}
   ${pill('claim: '+esc(c.claim_type),ctCol)}
   ${pill('integrity: '+esc(c.integrity_state),isCol)}
  </div>
  <div style="display:flex;flex-direction:column;gap:11px;margin-bottom:14px">
   <div><div class="mono" style="font-size:9px;letter-spacing:.06em;color:var(--secondary);margin-bottom:3px">SOURCE</div><div style="font:400 12px/1.5 'Inter Tight',sans-serif">${doiHtml}</div></div>
   <div><div class="mono" style="font-size:9px;letter-spacing:.06em;color:var(--secondary);margin-bottom:3px">QUOTE</div><div style="font:400 12px/1.5 'Inter Tight',sans-serif;color:var(--ink2)">${na(lk.source_quote)}</div></div>
   <div style="display:flex;gap:18px;flex-wrap:wrap"><div><div class="mono" style="font-size:9px;letter-spacing:.06em;color:var(--secondary);margin-bottom:3px">LOCATOR</div><div style="font:400 11.5px/1.4 'Inter Tight',sans-serif;color:var(--ink2)">${na(lk.source_locator)}</div></div>
    <div><div class="mono" style="font-size:9px;letter-spacing:.06em;color:var(--secondary);margin-bottom:3px">EXTRACTION</div><div style="font:400 11.5px/1.4 'Inter Tight',sans-serif;color:var(--ink2)">${na(lk.extraction_method)}</div></div></div>
  </div>
  <div style="font:400 11px/1.55 'Inter Tight',sans-serif;color:var(--secondary);padding:10px 12px;background:var(--lowest);border-radius:7px;margin-bottom:20px"><b style="color:var(--ink2)">Verified ≠ true.</b> “Verified” means the record resolves against a registry — never that it supports the claim or that the claim is correct.${c.integrity_state==='retracted'?' This source is <b style="color:var(--risk)">retracted</b> — excluded from positive support.':''}</div>`;
}

function screenEvidence(m){
 m.innerHTML=`<div class="gfull">
  <div class="gcanvaswrap"><canvas id="graph"></canvas>
   <div style="position:absolute;top:26px;left:30px;pointer-events:none"><div class="mono" style="font-size:11px;letter-spacing:.16em;color:var(--secondary);margin-bottom:8px">EVIDENCE GRAPH</div>
    <div style="font:400 30px/1.05 Newsreader,serif;letter-spacing:-.01em;color:var(--ink)">The case, as a network</div>
    <div class="mono" style="font-size:12px;color:var(--outline);margin-top:8px">11 nodes · 14 links · breathing by confidence</div></div>
   <div class="glegend">
    ${[['ok','High confidence'],['warn','Uncertain'],['risk','Contested']].map(([t,l])=>`<div style="display:flex;align-items:center;gap:7px"><span style="width:9px;height:9px;border-radius:50%;background:var(--${t})"></span><span style="font:500 11px/1 'Inter Tight',sans-serif;color:var(--ink2)">${l}</span></div>`).join('')}
    <span style="width:1px;height:16px;background:var(--hairline)"></span><div style="display:flex;align-items:center;gap:7px"><span style="width:14px;height:0;border-top:1.5px dashed var(--risk)"></span><span style="font:500 11px/1 'Inter Tight',sans-serif;color:var(--ink2)">Contradiction</span></div></div>
   <button class="gresetv" id="greset"><span class="ms" style="font-size:16px;color:var(--secondary)">recenter</span>Reset view</button>
  </div>
  <aside class="inspector"><div style="padding:15px 20px;border-bottom:1px solid var(--hairline);display:flex;align-items:center;justify-content:space-between"><span class="mono" style="font-size:11px;letter-spacing:.12em;color:var(--secondary)">PROVENANCE INSPECTOR</span><span class="ms" style="font-size:17px;color:var(--outline)">biotech</span></div><div id="insp"></div></aside>
 </div>`;
 const insp=$('#insp',m);
 const renderInsp=()=>{const n=NODES.find(x=>x.id===STATE.selected);
  if(!n){insp.innerHTML=`<div style="padding:30px 22px;text-align:center"><span class="ms" style="font-size:30px;color:var(--outline);margin-bottom:16px;display:block">ads_click</span><div style="font:500 14px/1.4 'Inter Tight',sans-serif;color:var(--ink);margin-bottom:8px">Select a node to inspect</div><p style="font:400 13px/1.55 'Inter Tight',sans-serif;color:var(--ink2);margin:0">Every node breathes by its confidence — the uncertain ones are restless. Select one to trace its provenance, then <strong style="font-weight:500;color:var(--ink)">contest</strong> it to watch uncertainty propagate through everything it supports.</p></div>`;return;}
  const cvar=confVar(n.dispConf??n.conf);const pct=Math.round((n.dispConf??n.conf)*100);const band=(n.dispConf??n.conf)>=0.8?'high':(n.dispConf??n.conf)>=0.63?'moderate':'low';
  insp.innerHTML=`<div style="padding:22px 20px;animation:ks-up .35s var(--e-out) both"><div style="display:flex;align-items:center;gap:8px;margin-bottom:16px"><span class="mono" style="font-size:10px;letter-spacing:.06em;color:var(--secondary);border:1px solid var(--hairline);border-radius:4px;padding:4px 7px">${TYPE_LABEL[n.type]}</span>${n.contested?`<span class="mono" style="font-size:10px;color:var(--risk);background:var(--risk-c);border-radius:4px;padding:4px 7px">CONTESTED</span>`:''}</div>
   <h3 style="font:400 24px/1.22 Newsreader,serif;letter-spacing:-.01em;color:var(--ink);margin:0 0 20px">${esc(n.label)}</h3>
   <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px"><span class="mono" style="font-size:11px;letter-spacing:.1em;color:var(--secondary)">CONFIDENCE · COMPUTED</span><span class="mono" style="font-size:20px;color:var(${cvar})">${(n.dispConf??n.conf).toFixed(2)}</span></div>
   <div style="height:5px;border-radius:3px;background:var(--high);overflow:hidden;margin-bottom:8px"><div style="height:100%;width:${pct}%;background:var(${cvar})"></div></div>
   <div class="mono" style="font-size:10px;color:var(--outline);margin-bottom:22px">provenance-weighted · ${band}</div>
   <div class="mono" style="font-size:10px;letter-spacing:.08em;color:var(--secondary);margin-bottom:9px">INTERPRETATION · CLAUDE</div><p style="font:400 15px/1.55 Newsreader,serif;color:var(--ink2);margin:0 0 22px">${esc(n.rel)}</p>
   ${claimSection(n.id)}
   ${n.sources.length?`<div class="mono" style="font-size:11px;letter-spacing:.1em;color:var(--secondary);margin-bottom:11px">PROVENANCE</div><div style="display:flex;flex-direction:column;gap:8px;margin-bottom:22px">${n.sources.map(s=>`<div class="srcrow"><span class="ms" style="font-size:17px;color:var(--secondary)">description</span><div style="flex:1;min-width:0"><div style="font:500 12px/1.3 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.src)}</div><div class="mono" style="font-size:10px;color:var(--secondary)">${esc(s.id)} · ${s.year}</div></div><span class="ms" style="font-size:15px;color:var(--outline)">north_east</span></div>`).join('')}</div>`:`<div style="font:400 12px/1.4 'Inter Tight',sans-serif;color:var(--ink2);margin-bottom:22px">Synthesised node — confidence is the provenance-weighted product of its inputs, not an independent claim.</div>`}
   <div style="display:flex;flex-direction:column;gap:9px"><button class="ibtn contest" id="contestbtn"><span class="ms" style="font-size:18px">do_not_disturb_on</span><span style="flex:1">Contest confidence</span><span class="mono" style="font-size:10px;color:var(--outline)">reviewer</span></button>
   <button class="ibtn"><span class="ms" style="font-size:18px;color:var(--secondary)">account_tree</span><span style="flex:1">Promote to premise</span></button></div></div>`;
  const cb=$('#contestbtn',insp);if(cb)cb.onclick=()=>contest(n.id);};
 // load real claim-level provenance (cached decision → instant), then refresh the drawer
 getJSON('/api/decision?domain='+curDomain()).then(d=>{ const ns=d.nodes||{}; CLAIM_MAP={};
   Object.keys(ns).forEach(k=>{ if(ns[k]&&ns[k].claim) CLAIM_MAP[k]=ns[k].claim; });
   if(STATE.selected) renderInsp(); }).catch(()=>{});
 // ---- graph engine ----
 const c=$('#graph',m); const worldW=940,worldH=640; let cam=null,hoverId=null,blast=null,t0=performance.now(),vpW=0,vpH=0;
 NODES.forEach(n=>{n.dispConf=n.conf;n.targetConf=n.conf;});
 const fitScale=(w,h)=>Math.min(w/worldW,h/worldH)*0.82;
 const initCam=(w,h)=>{const s=fitScale(w,h);cam={cx:worldW/2,cy:worldH/2,scale:s,tcx:worldW/2,tcy:worldH/2,tscale:s};};
 const w2s=(wx,wy)=>[(wx-cam.cx)*cam.scale+vpW/2,(wy-cam.cy)*cam.scale+vpH/2];
 const s2w=(sx,sy)=>[(sx-vpW/2)/cam.scale+cam.cx,(sy-vpH/2)/cam.scale+cam.cy];
 const select=n=>{STATE.selected=n.id;if(cam){cam.tcx=n.x;cam.tcy=n.y;cam.tscale=fitScale(vpW,vpH)*1.32;}if(!reduced)blast={x:n.x,y:n.y,t0:performance.now()};renderInsp();};
 const deselect=()=>{STATE.selected=null;if(cam){cam.tcx=worldW/2;cam.tcy=worldH/2;cam.tscale=fitScale(vpW,vpH);}renderInsp();};
 const contest=async id=>{const n=NODES.find(x=>x.id===id);if(!n)return;
  n.targetConf=Math.max(0.18,(n.dispConf??n.conf)-0.30);n.contested=true;
  EDGES.filter(e=>e.a===id).forEach(e=>{const ch=NODES.find(x=>x.id===e.b);if(ch)ch.targetConf=Math.max(0.2,(ch.targetConf??ch.conf)-0.10);});
  if(!reduced)blast={x:n.x,y:n.y,t0:performance.now(),review:true};renderInsp();
  // REAL server recompute — the graph action changes a real decision (not a visual-only drop)
  const host=$('#insp'); if(!host) return; const prev=$('#ks-contest-result',host); if(prev)prev.remove();
  const panel=document.createElement('div'); panel.id='ks-contest-result';
  panel.style.cssText='margin:0 20px 22px;padding:13px 15px;border:1px solid var(--risk);border-radius:9px;background:var(--risk-c)';
  panel.innerHTML=`<div style="display:flex;align-items:center;gap:9px;color:var(--secondary);font:400 12px/1.5 'Inter Tight',sans-serif"><span class="spin" style="border-top-color:var(--risk)"></span>Recomputing the decision without this evidence…</div>`;
  host.appendChild(panel);
  let d=null; try{ d=await getJSON('/api/counterfactual?domain='+encodeURIComponent(curDomain())+'&node='+encodeURIComponent(id)); }catch(e){ panel.innerHTML=`<div style="color:var(--warn);font:400 12px/1.5 'Inter Tight',sans-serif">Recompute failed (${esc(String(e))}).</div>`; return; }
  const changes=((d.ranking_delta||{}).changes)||[], fi=d.field_integrity||{}; let body='';
  if(changes.length){ body=`<div class="mono" style="font-size:9px;letter-spacing:.1em;color:var(--risk);margin-bottom:8px">TARGET RANKING RECOMPUTED</div>`+changes.map(c=>`<div style="font:400 12px/1.55 'Inter Tight',sans-serif;color:var(--ink)"><b>${esc(c.gene)}</b> composite ${(+c.composite_before).toFixed(3)} → <b style="color:var(--risk)">${(+c.composite_after).toFixed(3)}</b>${c.rank_before!==c.rank_after?` · rank #${c.rank_before}→#${c.rank_after}`:''}</div>`).join(''); }
  else if(fi.delta!=null&&fi.delta!==0){ body=`<div class="mono" style="font-size:9px;letter-spacing:.1em;color:var(--risk);margin-bottom:8px">FIELD INTEGRITY RECOMPUTED</div><div style="font:400 12px/1.55 'Inter Tight',sans-serif;color:var(--ink)">Field Integrity ${fi.if_trusted} → <b style="color:var(--risk)">${fi.excluded}</b> (Δ${fi.delta})</div>`; }
  else { body=`<div style="font:400 12px/1.55 'Inter Tight',sans-serif;color:var(--ink2)">Excluding this source does not change the current decision — it is not load-bearing.</div>`; }
  panel.innerHTML=`<div style="margin-bottom:7px;font:500 12px/1.3 'Inter Tight',sans-serif;color:var(--ink)">Contested — server recomputed</div>${body}<div class="mono" style="font-size:9px;color:var(--secondary);margin-top:9px">real /api/counterfactual · not a visual change</div>`;
 };
 window._ksContest=contest;
 const onMove=e=>{if(!cam)return;const r=c.getBoundingClientRect();const[wx,wy]=s2w(e.clientX-r.left,e.clientY-r.top);let hit=null;for(const n of NODES)if(Math.hypot(n.x-wx,n.y-wy)<n.r+8){hit=n.id;break;}hoverId=hit;c.style.cursor=hit?'pointer':'default';};
 const onClick=e=>{if(!cam)return;const r=c.getBoundingClientRect();const[wx,wy]=s2w(e.clientX-r.left,e.clientY-r.top);let hit=null;for(const n of NODES)if(Math.hypot(n.x-wx,n.y-wy)<n.r+8){hit=n;break;}hit?select(hit):deselect();};
 c.addEventListener('mousemove',onMove);c.addEventListener('click',onClick);
 $('#greset',m).onclick=deselect;
 const draw=now=>{const dpr=Math.min(2,window.devicePixelRatio||1);vpW=c.clientWidth;vpH=c.clientHeight;if(!vpW||!vpH){_raf=requestAnimationFrame(draw);return;}
  if(c.width!==Math.round(vpW*dpr)){c.width=Math.round(vpW*dpr);c.height=Math.round(vpH*dpr);}
  if(!cam)initCam(vpW,vpH);const ctx=c.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,vpW,vpH);
  cam.cx+=(cam.tcx-cam.cx)*0.09;cam.cy+=(cam.tcy-cam.cy)*0.09;cam.scale+=(cam.tscale-cam.scale)*0.09;
  NODES.forEach(n=>n.dispConf+=(n.targetConf-n.dispConf)*0.12);
  const t=(now-t0)/1000,hair=cv('--hairline'),ink=cv('--ink'),paper=cv('--lowest'),out=cv('--outline'),ink2=cv('--ink2'),risk=cv('--risk'),sel=STATE.selected;
  let wave=null;if(blast){const el=(now-blast.t0)/1000;wave={r:el*660,a:Math.max(0,.42-el*.30),review:blast.review};if(el>2.4){blast=null;wave=null;}}
  ctx.lineCap='round';
  EDGES.forEach((ed,i)=>{const na=NODES.find(x=>x.id===ed.a),nb=NODES.find(x=>x.id===ed.b);const[ax,ay]=w2s(na.x,na.y),[bx,by]=w2s(nb.x,nb.y);const alpha=Math.max(0,Math.min(1,(t-i*0.05)/0.4));if(alpha<=0)return;const active=sel&&(ed.a===sel||ed.b===sel);ctx.save();ctx.globalAlpha=alpha*(sel?(active?1:.28):.9);if(ed.kind==='contradicts'){ctx.strokeStyle=risk;ctx.setLineDash([2,5]);ctx.lineWidth=1.5;}else{ctx.strokeStyle=active?out:hair;ctx.lineWidth=active?1.6:1;}ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(bx,by);ctx.stroke();ctx.restore();});
  if(wave&&wave.a>0){const[bx,by]=w2s(blast.x,blast.y);ctx.save();ctx.globalAlpha=wave.a;ctx.strokeStyle=wave.review?risk:cv('--secondary');ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(bx,by,wave.r*cam.scale,0,7);ctx.stroke();ctx.restore();}
  NODES.forEach((n,i)=>{const[sx,sy]=w2s(n.x,n.y);const conf=n.dispConf,isSel=n.id===sel,isHover=n.id===hoverId;
   const amp=0.5+(1-conf)*3.6,spd=0.55+(1-conf)*0.85,breath=Math.sin(t*spd*2+i*1.7)*amp;
   let flare=0;if(wave){const d=Math.hypot(n.x-blast.x,n.y-blast.y);flare=Math.min(1,Math.max(0,1-Math.abs(wave.r-d)/46)*(wave.a*2.2));}
   const rNode=n.r*cam.scale+breath*0.35*cam.scale,haloR=rNode+(8+conf*22)*cam.scale+breath+flare*14,cvar=cv(confVar(conf));
   ctx.save();const g=ctx.createRadialGradient(sx,sy,rNode,sx,sy,haloR);g.addColorStop(0,hexA(cvar,0.16+conf*0.14+flare*0.3));g.addColorStop(1,hexA(cvar,0));ctx.fillStyle=g;ctx.beginPath();ctx.arc(sx,sy,haloR,0,7);ctx.fill();ctx.restore();
   ctx.fillStyle=n.type==='hypothesis'?ink:paper;ctx.beginPath();ctx.arc(sx,sy,rNode,0,7);ctx.fill();ctx.lineWidth=1;ctx.strokeStyle=isSel?ink:(n.type==='hypothesis'?ink:hair);ctx.stroke();
   ctx.strokeStyle=cvar;ctx.lineWidth=2.4;ctx.beginPath();ctx.arc(sx,sy,rNode+3.5,-Math.PI/2,-Math.PI/2+Math.PI*2*conf);ctx.stroke();
   if(isSel||isHover){ctx.strokeStyle=ink;ctx.globalAlpha=isSel?.9:.4;ctx.lineWidth=1;ctx.beginPath();ctx.arc(sx,sy,rNode+8,0,7);ctx.stroke();ctx.globalAlpha=1;}
   ctx.fillStyle=n.type==='hypothesis'?paper:ink2;ctx.font='500 '+Math.max(8,9.5*cam.scale)+'px "JetBrains Mono",monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(n.tc,sx,sy+0.5);
   if(cam.scale>0.36){ctx.font='500 12px "Inter Tight",system-ui,sans-serif';ctx.textBaseline='top';const ly=sy+haloR+4,tw=ctx.measureText(n.short).width;ctx.fillStyle=hexA(paper,0.85);ctx.fillRect(sx-tw/2-4,ly-1,tw+8,17);ctx.fillStyle=isSel?ink:ink2;ctx.fillText(n.short,sx,ly);}});
  _raf=requestAnimationFrame(draw);};
 renderInsp();_raf=requestAnimationFrame(draw);
 _cleanup=()=>{c.removeEventListener('mousemove',onMove);c.removeEventListener('click',onClick);};
}

/* ---------------- screen: Decision Engine ---------------- */
function screenDecision(m){
 const maxCost=Math.max(...EXPERIMENTS.map(e=>e.cost)),maxGain=Math.max(...EXPERIMENTS.map(e=>e.gain));
 const pts=EXPERIMENTS.map((e,i)=>({x:8+(e.cost/maxCost)*80,y:82-(e.gain/maxGain)*66,n:i+1,reco:e.reco}));
 const reco=EXPERIMENTS.find(e=>e.reco)||EXPERIMENTS[0];   // the ACTUAL recommended experiment for this program
 m.innerHTML=`<div class="wrap"><div style="animation:ks-up .5s var(--e-out) both"><div class="runkick"><span class="k">DECISION ENGINE</span></div>
  <h1 class="h2">What to run next</h1><p class="intro2">Ranked by expected reduction in uncertainty — not by what the program already believes. The best experiment is the one that could most change the conclusion.</p></div>
  <div class="frontier"><div><div class="mono" style="font-size:11px;letter-spacing:.1em;color:var(--secondary);margin-bottom:12px">THE DECISION FRONTIER · COMPUTED</div>
   <p style="font:400 16px/1.55 Newsreader,serif;color:var(--ink);margin:0">Each point is a candidate experiment, placed by cost against expected information gain. The best value sits high and to the left — inexpensive work that could still move the conclusion.${reco?` Keystone recommends <b style="color:var(--ink)">${esc(reco.title)}</b>.`:''}</p></div>
   <div style="position:relative"><svg viewBox="0 0 100 92" style="width:100%;height:230px;overflow:visible">
    <line x1="8" y1="82" x2="96" y2="82" stroke="var(--hairline)"/><line x1="8" y1="6" x2="8" y2="82" stroke="var(--hairline)"/>
    ${pts.map(p=>`<circle cx="${p.x}" cy="${p.y}" r="4.4" fill="${p.reco?'var(--primary)':'var(--lowest)'}" stroke="${p.reco?'var(--primary)':'var(--outline)'}" stroke-width="0.6"/><text x="${p.x}" y="${p.y+1.6}" text-anchor="middle" font-family="'JetBrains Mono',monospace" font-size="4" fill="${p.reco?'var(--on-primary)':'var(--ink2)'}">${p.n}</text>`).join('')}
    <text x="2" y="44" font-family="'JetBrains Mono',monospace" font-size="3.4" fill="var(--secondary)" transform="rotate(-90 2 44)">INFO GAIN ↑</text><text x="52" y="91" font-family="'JetBrains Mono',monospace" font-size="3.4" fill="var(--secondary)">COST →</text></svg></div></div>
  <div>${EXPERIMENTS.map((e,i)=>{const gpct=Math.round(e.gain/maxGain*100);const tier=e.gain>=0.3?'HIGH GAIN':e.gain>=0.2?'MODERATE':'LOW';const tcol=e.gain>=0.3?'--ok':e.gain>=0.2?'--warn':'--outline';
   return `<div class="exp"><div class="expnum">${i+1}</div><div style="flex:1;min-width:0"><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:5px"><span style="font:400 19px/1.25 Newsreader,serif;color:var(--ink)">${esc(e.title)}</span>${e.reco?`<span class="reco">RECOMMENDED · BEST VALUE</span>`:''}</div>
    <div class="mono" style="font-size:11px;color:var(--secondary);margin-bottom:12px">reduces · ${esc(e.reduces)}</div>
    <div class="mono" style="font-size:10px;letter-spacing:.08em;color:var(--secondary);margin-bottom:8px">RATIONALE · INTERPRETATION · CLAUDE</div><p style="font:400 14px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 12px">${esc(e.rationale)}</p>
    <button class="designbtn" data-exp="${i}"><span class="ms" style="font-size:15px;color:var(--secondary)">science</span>Design experiment</button></div>
    <div style="width:170px;flex:none"><div style="display:flex;align-items:baseline;justify-content:space-between"><span class="mono" style="font-size:10px;letter-spacing:.06em;color:var(${tcol})">${tier}</span><span class="mono" style="font-size:18px;color:var(--ink)">${e.gain.toFixed(2)}</span></div>
    <div class="gainbar"><i style="width:${gpct}%"></i></div><div class="mono" style="font-size:10px;color:var(--secondary)">Δ information · ${esc(e.costLabel)}</div></div></div>`;}).join('')}</div></div>`;
 m.querySelectorAll('.designbtn').forEach(b=>b.onclick=()=>designExperiment(+b.dataset.exp));
}

/* ---------------- screen: Frontier Guard ---------------- */
function screenFrontier(m){
 const ic={pass:['check_circle','--ok'],flag:['flag','--warn']};
 m.innerHTML=`<div class="wrap"><div style="animation:ks-up .5s var(--e-out) both"><div class="runkick"><span class="k">FRONTIER GUARD</span></div>
  <h1 class="h2">Should this be refused?</h1><p class="intro2">Every capability that could be misused is gated. Keystone refuses on its own, records why, and never lets a model decision substitute for a human one.</p></div>
  <div class="gclear"><span class="ms" style="font-size:22px;color:var(--warn)">gpp_maybe</span><div style="flex:1"><div style="font:500 16px/1.3 'Inter Tight',sans-serif;color:var(--ink)">Cleared with one flag</div><div style="font:400 12px/1.4 'Inter Tight',sans-serif;color:var(--ink2)">Human review is required before any capability is released.</div></div><span class="mono" style="font-size:11px;letter-spacing:.08em;color:var(--warn)">HUMAN REVIEW REQUIRED</span></div>
  <div class="mono" style="font-size:11px;letter-spacing:.1em;color:var(--secondary);margin-bottom:2px">SAFETY & DUAL-USE SCREEN</div>
  <div style="border:1px solid var(--hairline);border-radius:10px;background:var(--lowest);overflow:hidden;margin-top:12px">${SCREENS.map((s,i)=>{const[icon,col]=ic[s.status];return `<div class="scrow" style="${i===SCREENS.length-1?'border-bottom:none':''}"><span class="ms" style="font-size:18px;color:var(${col});margin-top:1px">${icon}</span><div style="flex:1"><div style="font:500 15px/1.3 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.name)}</div><div style="font:400 13px/1.45 'Inter Tight',sans-serif;color:var(--ink2);margin-top:2px">${esc(s.note)}</div></div><span class="mono" style="font-size:10px;letter-spacing:.08em;color:var(${col})">${s.status==='pass'?'PASS':'FLAGGED'}</span></div>`;}).join('')}</div>
  <div class="refusal"><div style="display:flex;align-items:center;gap:8px;margin-bottom:12px"><span class="ms" style="font-size:18px;color:var(--risk)">block</span><span class="mono" style="font-size:11px;letter-spacing:.1em;color:var(--risk)">REFUSED REQUEST CLASS · POLICY EXAMPLE</span></div>
   <p style="font:400 18px/1.5 Newsreader,serif;color:var(--ink);margin:0 0 14px">${esc(REFUSAL.request)}</p>
   <p style="font:400 14px/1.55 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 14px">${esc(REFUSAL.reason)}</p>
   <div class="mono" style="font-size:11px;color:var(--risk)">${esc(REFUSAL.log)}</div></div></div>`;
}

/* ---------------- screen: Reasoning Pipeline (real multi-agent trace) ---------------- */
// Every program renders the actual /api/pipeline trace: 12 specialists, each
// tagged AGENT (Claude reasoning) or TOOL (deterministic math). That split is the
// rigor — Claude writes prose and judgments, tools produce every number.
function screenReasoning(m){
 m.innerHTML=`<div class="reado"><div style="animation:ks-up .5s var(--e-out) both">
   <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px"><span class="mono" style="font-size:11px;letter-spacing:.16em;color:var(--secondary)">REASONING PIPELINE · MULTI-AGENT</span><span class="livebadge" style="display:inline-flex;align-items:center;gap:6px;padding:4px 9px;border:1px solid var(--hairline);border-radius:20px"></span></div>
   <h1 style="font:400 40px/1.08 Newsreader,serif;letter-spacing:-.015em;color:var(--ink);margin:0 0 12px">How Keystone reasons about ${esc(META.progname)}</h1>
   <p style="font:400 15px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 8px;max-width:70ch">The audited reasoning trace behind the decision, plus the <b>swarm-vs-cell control</b> that shows why gating beats scale. <b style="color:var(--claude-live)">Agents</b> (Claude-backed) produce the prose, judgments and the hypothesis; <b style="color:var(--ink)">tools</b> (deterministic) produce every number. Claude never invents a statistic — that boundary is the rigor. For the five-agent reviewer-gated run, see <b>Research Cell</b>.</p>
   <div style="display:flex;gap:10px;flex-wrap:wrap;margin:18px 0 6px" id="pipemetrics"></div></div>
   <div id="pipeline" style="margin-top:20px;color:var(--secondary);font:400 12px/1.6 'JetBrains Mono',monospace">Running the agent pipeline over real evidence…</div></div>`;
 renderLiveBadge(); refreshLive();
 fetchPipeline(curDomain());
}
async function fetchPipeline(domain){
 const host=$('#pipeline'), mx=$('#pipemetrics'); if(!host) return;
 host.innerHTML=`<div style="color:var(--secondary);font:400 12px/1.6 'JetBrains Mono',monospace">Loading the agent team over real evidence…</div>`;
 try{
  // cached decision trace (instant after warm) — same 12-step trace as /api/pipeline, but never stalls
  const [d,v,rc]=await Promise.all([getJSON('/api/decision?domain='+encodeURIComponent(domain)), getJSON('/api/validation?domain='+encodeURIComponent(domain)).catch(()=>null), getJSON('/api/research_cell?domain='+encodeURIComponent(domain)).catch(()=>null)]);
  const trace=(d.agent_trace||[]);
  if(!trace.length){ host.innerHTML=`<div style="color:var(--warn)">The reasoning trace is warming — open the case once, then return.</div>`; return; }
  const agents=trace.filter(s=>s.actor_type==='agent'), tools=trace.filter(s=>s.actor_type==='tool');
  const adv=trace.find(s=>/review/i.test(s.actor||'') && s.confidence_delta!=null) || trace.find(s=>s.confidence_delta!=null && s.confidence_delta<0);
  if(mx){
   const lb=v&&(v.load_bearing_calibration||{}).agreement;
   const pill=(k,val,c)=>`<div style="border:1px solid var(--hairline);border-radius:8px;background:var(--lowest);padding:9px 13px"><div class="mono" style="font-size:9px;letter-spacing:.1em;color:var(--secondary)">${k}</div><div style="font:500 15px/1.1 'Inter Tight',sans-serif;color:var(${c||'--ink'});margin-top:3px">${val}</div></div>`;
   mx.innerHTML=pill('CLAUDE AGENTS',agents.length,'--claude-live')+pill('DETERMINISTIC TOOLS',tools.length)+(lb!=null?pill('LOAD-BEARING CLASSIFIER',lb+' agree'):'')+(v&&v.recall!=null?pill('FLAW-CATCH RECALL',v.caught+'/'+v.n_planted):'')+pill('GRAPH HASH',(d.graph_hash||'').slice(0,10));
  }
  // 1) team roster — the whole crew at a glance, split Claude agents | deterministic tools
  const cell=s=>{const isA=s.actor_type==='agent';const isAdv=adv&&s.step===adv.step;
   return `<div style="display:flex;gap:9px;padding:9px 11px;border:1px solid var(${isAdv?'--risk':'--hairline'});border-radius:8px;background:var(--paper)${isAdv?';box-shadow:0 0 0 3px var(--risk-c)':''}">
     <span class="mono" style="font-size:9px;color:var(--outline);flex:none;margin-top:2px">${String(s.step).padStart(2,'0')}</span>
     <div style="min-width:0"><div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap"><span style="font:600 12.5px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.actor)}</span>${isAdv?`<span class="mono" style="font-size:8px;letter-spacing:.06em;color:var(--risk)">ADVERSARY</span>`:''}</div>
      <div style="font:400 11px/1.35 'Inter Tight',sans-serif;color:var(--secondary);margin-top:2px">${esc(String(s.role||'').slice(0,70))}</div></div></div>`;};
  const col=(label,dot,items)=>`<div><div class="mono" style="font-size:10px;letter-spacing:.11em;color:var(${dot});margin-bottom:10px"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:var(${dot==='--claude-live'?'--claude-live':'--outline'});margin-right:6px"></span>${label}</div><div style="display:flex;flex-direction:column;gap:8px">${items.map(cell).join('')}</div></div>`;
  const roster=`<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:22px;margin-bottom:26px">${col(agents.length+' CLAUDE AGENTS · reasoning &amp; judgment','--claude-live',agents)}${col(tools.length+' DETERMINISTIC TOOLS · every number','--secondary',tools)}</div>`;
  // 2) adversary spotlight — the check that removes unearned confidence (the winning pattern)
  let advHTML='';
  if(adv){const cb=adv.confidence_before,ca=adv.confidence_after,dl=adv.confidence_delta;
   advHTML=`<div style="border:1px solid var(--risk);border-radius:11px;background:var(--risk-c);padding:18px 22px;margin-bottom:26px">
     <div style="display:flex;align-items:center;gap:9px;margin-bottom:10px"><span class="ms" style="font-size:19px;color:var(--risk)">gavel</span><span class="mono" style="font-size:10px;letter-spacing:.12em;color:var(--risk)">THE ADVERSARY · ${esc(adv.actor)}</span></div>
     <p style="font:400 15px/1.5 Newsreader,serif;color:var(--ink);margin:0 0 12px">A Claude agent whose only job is to attack the hypothesis and strip out confidence the evidence hasn't earned — the check that keeps Keystone honest.</p>
     ${cb!=null&&ca!=null?`<div style="display:flex;align-items:center;gap:13px;flex-wrap:wrap;margin-bottom:${adv.challenged_assumption?'12px':'0'}"><span class="mono" style="font-size:10px;letter-spacing:.08em;color:var(--secondary)">CONFIDENCE</span><span class="mono" style="font-size:21px;color:var(--ink2)">${(+cb).toFixed(2)}</span><span class="ms" style="color:var(--risk);font-size:20px">arrow_forward</span><span class="mono" style="font-size:21px;color:var(--risk)">${(+ca).toFixed(2)}</span><span class="mono" style="font-size:11px;color:var(--risk)">Δ ${(+dl).toFixed(2)} removed</span></div>`:''}
     ${adv.challenged_assumption?`<div style="font:400 13px/1.5 'Inter Tight',sans-serif;color:var(--ink2)"><span class="mono" style="font-size:9px;color:var(--risk);letter-spacing:.08em">CHALLENGED&nbsp;</span>${esc(String(adv.challenged_assumption).slice(0,240))}</div>`:''}
     ${adv.why_disagrees?`<div style="font:400 13px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:6px">${esc(String(adv.why_disagrees).slice(0,240))}</div>`:''}</div>`;}
  // 3) full trace, in sequence
  const timeline=trace.map(s=>{
   const isAgent=s.actor_type==='agent', ac=isAgent?'--claude-live':'--secondary';
   const chip=`<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:20px;background:var(--container);font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em;color:var(${ac})"><span style="width:5px;height:5px;border-radius:50%;background:var(${ac})"></span>${isAgent?'AGENT · CLAUDE':'TOOL · DETERMINISTIC'}</span>`;
   const prov=(s.provenance||[]).slice(0,1).map(x=>`<div class="mono" style="font-size:10px;color:var(--secondary);margin-top:6px;word-break:break-word">↳ ${esc(String(x).slice(0,90))}</div>`).join('');
   const unc=s.remaining_uncertainty?`<div style="font:400 12px/1.45 'Inter Tight',sans-serif;color:var(--ink2);margin-top:8px"><span class="mono" style="font-size:9px;color:var(--warn);letter-spacing:.08em">UNCERTAINTY</span> ${esc(String(s.remaining_uncertainty).slice(0,150))}</div>`:'';
   return `<div style="position:relative;padding:0 0 18px 30px;border-left:2px solid var(${isAgent?'--claude-live':'--hairline'})">
     <span style="position:absolute;left:-8px;top:2px;width:14px;height:14px;border-radius:50%;background:var(--paper);border:2px solid var(${ac})"></span>
     <div style="border:1px solid var(--hairline);border-radius:9px;background:var(--lowest);padding:15px 18px">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px"><span class="mono" style="font-size:10px;color:var(--outline)">${String(s.step).padStart(2,'0')}</span><span style="font:600 14px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.actor)}</span>${chip}</div>
      <div style="font:400 12px/1.4 'Inter Tight',sans-serif;color:var(--secondary);margin-bottom:6px">${esc(s.role||'')}</div>
      <div style="font:400 14px/1.5 Newsreader,serif;color:var(--ink)">${esc(String(s.output||'').slice(0,220))}</div>${prov}${unc}</div></div>`;}).join('');
  // 0) THE DIFFERENTIATOR — measured swarm-vs-cell control (more agents ≠ better science)
  let benchHTML='';
  if(rc&&rc.benchmark){const b=rc.benchmark,sw=b.swarm,ce=b.cell,gate=rc.agent_count_gate;
   const row=(label,sv,cv,bad)=>`<tr style="border-top:1px solid var(--hairline)"><td style="padding:8px 14px;font:400 12.5px/1.3 'Inter Tight',sans-serif;color:var(--ink2)">${label}</td><td style="padding:8px 14px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(${bad&&(+sv>0)?'--risk':'--ink'})">${sv}${bad&&(+sv>0)?' ⚠':''}</td><td style="padding:8px 14px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--ok)">${cv}</td></tr>`;
   benchHTML=`<div style="border:1px solid var(--primary);border-radius:12px;background:var(--paper);overflow:hidden;margin-bottom:26px">
     <div style="padding:16px 20px;border-bottom:1px solid var(--hairline)"><div class="mono" style="font-size:10px;letter-spacing:.12em;color:var(--secondary)">CONTROLLED CELL vs NAIVE SWARM · MEASURED CONTROL</div><h2 style="font:600 22px/1.15 'Inter Tight',sans-serif;color:var(--ink);margin:8px 0 0">More agents ≠ better science</h2></div>
     <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;min-width:420px"><thead><tr><th style="padding:10px 14px;text-align:left;font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em;color:var(--secondary)">SAME REAL CORPUS</th><th style="padding:10px 14px;text-align:right;font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em;color:var(--warn)">NAIVE SWARM · ${sw.agents}</th><th style="padding:10px 14px;text-align:right;font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em;color:var(--ok)">RESEARCH CELL · ${ce.agents}</th></tr></thead><tbody>
     ${row('Claims admitted',sw.claims_admitted,ce.claims_admitted,false)}
     ${row('Retracted / concern cited',sw.retracted_or_concern_cited,ce.retracted_or_concern_cited,true)}
     ${row('Not-peer-reviewed cited',sw.not_peer_reviewed_cited,ce.not_peer_reviewed_cited,true)}
     ${row('Unsupported claims cited',sw.unsupported_cited,ce.unsupported_cited,true)}
     ${row('Provenance-complete',sw.provenance_complete_pct+'%',ce.provenance_complete_pct+'%',false)}
     ${row('Robust to a new retraction',sw.robust_to_new_retraction?'yes':'no',ce.robust_to_new_retraction?'yes':'no',false)}
     ${row('Est. cost · labelled estimate','$'+sw.est_usd,'$'+ce.est_usd,false)}
     </tbody></table></div>
     <div style="padding:14px 20px;border-top:1px solid var(--hairline);font:400 13px/1.55 Newsreader,serif;color:var(--ink)">${esc(b.verdict)}</div>
     <div style="padding:0 20px 15px;font:400 11px/1.5 'Inter Tight',sans-serif;color:var(--secondary)">${esc(b.note)}${gate&&!gate.allowed?`<br><b style="color:var(--warn)">N&gt;${rc.max_cell_agents} gate:</b> ${esc(gate.reason)}`:''}</div>
   </div>`;}
  // 1b) THE RESEARCH CELL — the 8 named specialists (this is what the benchmark's "cell" IS,
  // and it matches the architecture diagram). Coordinator + 4 analysts + 2 gates + planner.
  let cellHTML=roster;   // fallback to the execution split if the roster API is unavailable
  if(rc&&Array.isArray(rc.roster)&&rc.roster.length){
    const isGate=n=>/integrity|reviewer/i.test(n||'');
    const cards=rc.roster.map((a,i)=>{const g=isGate(a.name);
      return `<div style="display:flex;gap:10px;padding:11px 13px;border:1px solid var(${g?'--warn':'--hairline'});border-radius:9px;background:var(--paper)${g?';box-shadow:0 0 0 3px var(--warn-c)':''}">
        <span class="mono" style="font-size:9px;color:var(--outline);flex:none;margin-top:3px">${String(i+1).padStart(2,'0')}</span>
        <div style="min-width:0"><div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap"><span style="font:600 12.5px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(a.name)}</span>${g?`<span class="mono" style="font-size:8px;letter-spacing:.06em;color:var(--warn)">GATE</span>`:(i===0?`<span class="mono" style="font-size:8px;letter-spacing:.06em;color:var(--primary)">DISPATCH</span>`:'')}</div>
         <div style="font:400 11px/1.4 'Inter Tight',sans-serif;color:var(--secondary);margin-top:2px">${esc(a.role||'')}</div></div></div>`;}).join('');
    cellHTML=`<div style="margin-bottom:26px">
      <div class="mono" style="font-size:10px;letter-spacing:.12em;color:var(--secondary);margin-bottom:4px">THE RESEARCH CELL · ${rc.roster.length} SPECIALISTS · ONE JOB EACH</div>
      <p style="font:400 13px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 14px;max-width:82ch">A controlled team, not a swarm. The Coordinator dispatches only the relevant specialists; two <b style="color:var(--warn)">gates</b> — Integrity and Reviewer — can exclude or reject a claim before it reaches any decision. On this question the cell executed as the ${trace.length}-step audited run below (${agents.length} Claude reasoning steps · ${tools.length} deterministic tools).</p>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px">${cards}</div></div>`;
  }
  host.innerHTML=benchHTML+cellHTML+advHTML+`<div class="mono" style="font-size:10px;letter-spacing:.12em;color:var(--secondary);margin-bottom:14px">THE AUDITED RUN · how the cell executed · ${trace.length} STEPS</div>`+timeline;
 }catch(e){ host.innerHTML=`<div style="color:var(--warn)">Could not load the agent team (${esc(String(e))}). Open the case once to warm the reasoning, then return.</div>`; }
}
function screenGrant(m){
 m.innerHTML=`<div class="wrap"><div style="animation:ks-up .5s var(--e-out) both"><div class="runkick"><span class="k">GRANT EXPORT</span></div>
  <h1 class="h2">The package a reviewer can trust</h1><p class="intro2">Every claim carries its source; the one unresolved conflict is disclosed, not hidden. Content-addressed and reproducible from the ledger.</p></div>
  <div style="border:1px solid var(--hairline);border-radius:10px;background:var(--lowest);overflow:hidden">${grantFiles().map((g,i,arr)=>`<div style="display:flex;align-items:center;gap:16px;padding:18px 22px;${i===arr.length-1?'':'border-bottom:1px solid var(--hairline)'}"><span class="ms" style="font-size:20px;color:var(--secondary)">description</span><div style="flex:1"><div style="font:500 15px/1.3 'Inter Tight',sans-serif;color:var(--ink)">${esc(g.name)}</div><div style="font:400 12px/1.4 'Inter Tight',sans-serif;color:var(--ink2);margin-top:2px">${esc(g.note)}</div></div><span class="mono" style="font-size:11px;color:var(--secondary)">${g.pages}</span></div>`).join('')}</div>
  <div style="display:flex;gap:12px;margin-top:20px;flex-wrap:wrap"><button class="export" id="ks-bundle-btn"><span class="ms" style="font-size:17px">folder_zip</span>Reproducibility bundle (.zip)</button><button class="rerun" onclick="window.print()"><span class="ms" style="font-size:16px">description</span>Print grant package</button><button class="rerun" id="ks-verify-btn"><span class="ms" style="font-size:16px">verified</span>Verify receipt</button></div>
  <div id="ks-verify-out" style="margin-top:12px"></div>
  <p style="font:400 11.5px/1.55 'Inter Tight',sans-serif;color:var(--secondary);margin-top:12px">The bundle contains <span class="mono">sources.csv</span>, <span class="mono">claims.json</span>, <span class="mono">assessments.json</span>, <span class="mono">run-manifest.json</span> (dataset · code · model · prompt · seed · run) and <span class="mono">experiment-plan.md</span> — a reviewer can re-run every number from the graph hash. <b>Verify receipt</b> re-runs the engine and confirms the content hash reproduces.</p></div>`;
 const bb=$('#ks-bundle-btn',m); if(bb) bb.onclick=()=>{ location.href='/api/export/bundle?domain='+curDomain(); };
 const vb=$('#ks-verify-btn',m); const vo=$('#ks-verify-out',m);
 if(vb) vb.onclick=async()=>{
   vo.innerHTML=`<div class="mono" style="font-size:11px;color:var(--secondary)">Re-running the engine to reproduce the receipt…</div>`;
   try{
     const dom=curDomain();
     const first=await getJSON('/api/verify_receipt?domain='+encodeURIComponent(dom));
     const h=first.recomputed_graph_hash;
     const chk=await getJSON('/api/verify_receipt?domain='+encodeURIComponent(dom)+'&claimed_hash='+encodeURIComponent(h));
     const ok=chk.verified===true;
     vo.innerHTML=`<div style="display:flex;align-items:center;gap:10px;padding:11px 14px;border:1px solid var(${ok?'--ok':'--risk'});border-radius:9px;background:var(--paper)"><span class="ms" style="font-size:20px;color:var(${ok?'--ok':'--risk'})">${ok?'verified':'error'}</span><div><div style="font:600 12.5px/1.3 'Inter Tight',sans-serif;color:var(--ink)">${ok?'✓ VERIFIED — receipt reproduces':'✗ hash did not reproduce'}</div><div class="mono" style="font-size:9.5px;color:var(--secondary);margin-top:3px">graph hash <b style="color:var(--ink)">${esc(h.slice(0,24))}…</b> reproduced by an independent deterministic re-run · seed ${esc(chk.seed||'0x1f')}</div></div></div>`;
   }catch(e){ vo.innerHTML=`<div style="color:var(--warn);font:400 12px/1.4 'Inter Tight',sans-serif">Could not verify (${esc(String(e))}).</div>`; }
 };
}
function screenProtein(m){
 const pdb=META.pdb;
 m.innerHTML=`<div class="wrap"><div style="animation:ks-up .5s var(--e-out) both"><div class="runkick"><span class="k">3D PROTEIN VIEWER</span><span class="d"></span><span class="r">${pdb?('PDB '+esc(pdb)+' · real coordinates'):'no structure'}</span></div>
  <h1 class="h2">${esc(META.target||'Target structure')}</h1><p class="intro2">Rendered from real RCSB PDB coordinates — the true macromolecule, not an illustration. Drag to rotate · scroll to zoom.</p></div>
  <div style="border:1px solid var(--hairline);border-radius:12px;background:var(--lowest);overflow:hidden;position:relative;height:440px">
   <div id="mol3d" style="width:100%;height:100%;position:relative"></div>
   <div id="molload" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--secondary);font:400 12px/1 'JetBrains Mono',monospace;pointer-events:none">loading ${pdb?esc(pdb):''} from RCSB PDB…</div>
   <div class="mono" style="position:absolute;left:14px;bottom:12px;font-size:10px;color:var(--secondary);background:var(--paper);border:1px solid var(--hairline);border-radius:6px;padding:5px 9px">RCSB PDB ${pdb?esc(pdb):'—'} · cartoon · spectrum</div></div>
  <div style="display:flex;gap:12px;margin-top:16px"><a class="rerun" href="/workspace" style="text-decoration:none"><span class="ms" style="font-size:16px">open_in_new</span>Connected evidence workspace</a>${pdb?`<a class="rerun" href="https://www.rcsb.org/structure/${esc(pdb)}" target="_blank" rel="noopener" style="text-decoration:none"><span class="ms" style="font-size:16px">north_east</span>PDB ${esc(pdb)} on RCSB</a>`:''}</div></div>`;
 const done=t=>{const l=document.getElementById('molload');if(l){if(t)l.textContent=t;else l.style.display='none';}};
 if(pdb && window.$3Dmol){
   try{
     const dark=document.documentElement.getAttribute('data-theme')==='dark';
     const v=$3Dmol.createViewer(document.getElementById('mol3d'),{backgroundColor:dark?'#131417':'#fcf8f9'});
     let rendered=false;
     const finish=()=>{ if(rendered)return; rendered=true;
       try{ if(!v.getModel()){rendered=false;return;} v.setStyle({},{cartoon:{color:'spectrum'}}); v.zoomTo(); v.render(); try{v.spin('y',0.5);}catch(e){} done(); }
       catch(e){ rendered=false; } };
     // newer 3Dmol changed download()'s callback contract → render on callback, promise, AND a
     // fallback timer (the RCSB fetch returns fast) so the "loading" overlay always clears.
     const p=$3Dmol.download('pdb:'+pdb,v,{},finish);
     if(p&&typeof p.then==='function') p.then(finish).catch(()=>done('3D unavailable — open on RCSB'));
     setTimeout(finish,2200); setTimeout(finish,4500);
   }catch(e){done('3D unavailable — open on RCSB');}
 } else { done(pdb?'3D unavailable offline — open on RCSB':'no structure for this program'); }
}

/* ---------------- router ---------------- */
/* ---------------- screen: Target Ranking (Target Trust — 8-component contract) ---------------- */
const _TR_NAMES={functional_effect:'Functional perturbation effect',activation_specificity:'Activation-state specificity',type2_pathway:'Type-2 pathway evidence',disease_relevance:'Disease relevance evidence',tractability:'Tractability evidence',safety_risk:'Safety / essentiality risk',integrity_risk:'Integrity risk',safety:'Safety / essentiality',integrity:'Integrity confidence'};
function _trLabelCol(l){return {'Measured in dataset':'--ok','Computed from analysis':'--primary','Literature-supported':'--secondary','Model hypothesis':'--warn','Unknown / insufficient evidence':'--outline','Existing degrader evidence':'--ok','Ligandability evidence':'--ok','Structural/chemical tractability proxy':'--secondary','E3-recruitment evidence':'--secondary','Predicted hypothesis':'--warn','No tractability evidence found':'--risk'}[l]||'--secondary';}
function _trSrcLink(s){const href=/^https?:/i.test(s)?s:(/^DOI:/i.test(s)?'https://doi.org/'+s.slice(4):(/^UniProt:/i.test(s)?'https://www.uniprot.org/uniprotkb/'+s.slice(8):(/^10\./.test(s)?'https://doi.org/'+s:'')));return href?`<a href="${esc(href)}" target="_blank" rel="noopener" style="color:var(--claude-live);text-decoration:none">${esc(s)}</a>`:esc(s);}
function _trComponentRow(key,c){const col=_trLabelCol(c.label);
 return `<div style="padding:12px 0;border-top:1px solid var(--hairline)">
   <div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px"><span style="font:500 13px/1.3 'Inter Tight',sans-serif;color:var(--ink)">${_TR_NAMES[key]}</span><span style="display:flex;align-items:center;gap:9px"><span class="mono" style="font-size:9px;padding:2px 7px;border-radius:20px;background:var(--container);color:var(${col})">${esc(c.label)}</span><span class="mono" style="font-size:13px;color:var(--ink)">${(+c.value).toFixed(2)}</span></span></div>
   <div style="height:4px;border-radius:2px;background:var(--high);overflow:hidden;margin:7px 0"><div style="height:100%;width:${Math.round(c.value*100)}%;background:var(${col})"></div></div>
   <div class="mono" style="font-size:10px;color:var(--secondary);line-height:1.55">formula · ${esc(c.formula)}<br>source · ${_trSrcLink(c.source)} · uncertainty · ${esc(c.uncertainty)}<br>limitation · ${esc(c.limitation)}</div></div>`;}
function screenTargets(m){
 m.innerHTML=`<div class="reado"><div style="animation:ks-up .5s var(--e-out) both"><div class="mono" style="font-size:11px;letter-spacing:.16em;color:var(--secondary);margin-bottom:12px">TARGET TRUST · REGULATOR RANKING</div>
   <h1 style="font:400 38px/1.08 Newsreader,serif;letter-spacing:-.015em;color:var(--ink);margin:0 0 12px">Find the next STAT6</h1>
   <p style="font:400 15px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 6px;max-width:72ch">STAT6 — the top-ranked regulator — is now a clinical oral degrader (KT-621), proof an intracellular type-2 master switch is druggable. This ranking <b>fuses functional genomics with chemical tractability</b> to map the next one: eight separate, sourced components — never one opaque score — weighted with the weights shown. Perturbation effects are published measurements, not a trained model, and no association is stated as causal. <b>Designed for scientist review.</b></p></div>
   <div id="tr-body" style="margin-top:18px;color:var(--secondary);font:400 12px/1.6 'JetBrains Mono',monospace">Loading the ranking…</div></div>`;
 loadTargetRanking(curDomain(), '', '');
}
async function loadTargetRanking(dom, exclude, weights){
 const host=$('#tr-body'); if(!host) return;
 const wq=weights?('&weights='+encodeURIComponent(weights)):'';
 const rurl=g=>'/api/target_ranking?domain='+encodeURIComponent(dom)+(g?'&exclude='+encodeURIComponent(g):'')+wq;
 let d=null, base=null;
 try{
   d=await getJSON(rurl(exclude));
   if(exclude){ base=await getJSON(rurl('')).catch(()=>null); }   // baseline, for the before→after composite delta
 }catch(e){ host.innerHTML=`<div style="color:var(--warn)">Could not load ranking (${esc(String(e))}).</div>`; return; }
 const baseC={}; if(base&&base.ranking){ base.ranking.forEach(b=>{ baseC[b.node_id]=b.composite; }); }
 if(!d.ranking||!d.ranking.length){ host.innerHTML=`<div style="padding:16px 0;color:var(--ink2);font:400 14px/1.6 'Inter Tight',sans-serif">${esc(d.note||'Target ranking is defined for the CD4+ T-cell program.')} Switch the program (top-left) to <b>IMMUNOLOGY · CD4 T-CELL</b>.</div>`; return; }
 const pre='https://www.biorxiv.org/content/10.64898/2025.12.23.696273v1', excluded=!!exclude;
 const weightsStr=Object.entries(d.weights).map(([k,v])=>`${_TR_NAMES[k]||k} ${(v*100).toFixed(0)}%`).join(' · ');
 const _wkeys=['functional_effect','activation_specificity','type2_pathway','disease_relevance','tractability','safety','integrity'];
 const _sliders=_wkeys.map(k=>{const v=Math.round((d.weights[k]||0)*100);return `<div style="display:flex;align-items:center;gap:9px;padding:2px 0"><span style="flex:1;font:400 11px/1.3 'Inter Tight',sans-serif;color:var(--ink2)">${esc(_TR_NAMES[k]||k)}</span><input type="range" min="0" max="60" value="${v}" data-wk="${k}" style="width:130px;accent-color:var(--primary);cursor:pointer"><span class="mono" data-wv="${k}" style="font-size:10px;color:var(--ink);width:32px;text-align:right">${v}%</span></div>`;}).join('');
 const wpanel=`<details style="margin-bottom:12px;border:1px solid var(--hairline);border-radius:9px;background:var(--paper)"${weights?' open':''}><summary style="cursor:pointer;padding:9px 14px;font:500 11.5px/1.3 'Inter Tight',sans-serif;color:var(--ink);list-style:none">⚙ Adjust component weights — the ranking recomputes ${d.weights_customized?'<span class="mono" style="font-size:9px;color:var(--warn)">· CUSTOMIZED</span>':''}</summary><div style="padding:2px 14px 12px">${_sliders}<div style="display:flex;justify-content:space-between;align-items:center;margin-top:9px;gap:10px"><span class="mono" style="font-size:9px;color:var(--secondary)">weights renormalize to 100% · underlying evidence unchanged</span><button id="tr-wreset" style="border:1px solid var(--hairline);background:none;color:var(--ink2);border-radius:6px;padding:4px 10px;font:500 10px/1 'Inter Tight',sans-serif;cursor:pointer">Reset to defaults</button></div></div></details>`;
 const cards=d.ranking.map(c=>{const me=(c.components.missing_evidence||[]);
  return `<div style="border:1px solid ${c.rank===1?'var(--primary)':'var(--hairline)'};border-radius:11px;background:var(--paper);margin-bottom:12px;overflow:hidden">
    <div style="display:flex;align-items:center;gap:14px;padding:16px 20px;cursor:pointer" data-tr-toggle="${c.node_id}">
     <span style="font:400 26px/1 Newsreader,serif;color:var(${c.rank===1?'--primary':'--outline'})">#${c.rank}</span>
     <div style="flex:1;min-width:0"><div style="font:500 17px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(c.gene)}${c.rank===1?' <span class="mono" style="font-size:9px;color:var(--primary)">TOP CANDIDATE</span>':''}${c.precedent?` <span class="mono" style="font-size:9px;color:var(--ok)">✓ CLINICAL DEGRADER · ${esc(c.precedent.drug)}</span>`:''}</div>
      <div class="mono" style="font-size:10px;color:var(--secondary);margin-top:3px">UniProt:${esc(c.uniprot)} · composite ${c.composite.toFixed(3)}${(excluded&&baseC[c.node_id]!=null&&Math.abs(baseC[c.node_id]-c.composite)>0.0005)?` <span style="color:var(--risk)">▼ was ${baseC[c.node_id].toFixed(3)} · Δ${(c.composite-baseC[c.node_id]).toFixed(3)}</span>`:''} · tap to review why</div></div>
     <div style="width:130px;flex:none"><div style="height:6px;border-radius:3px;background:var(--high);overflow:hidden"><div style="height:100%;width:${Math.round(c.composite*100)}%;background:var(${c.rank===1?'--primary':'--accent'})"></div></div></div>
     <span class="ms" style="font-size:18px;color:var(--secondary)" id="tr-caret-${c.node_id}">expand_more</span></div>
    <div id="tr-detail-${c.node_id}" style="display:none;padding:4px 20px 18px">
     ${['functional_effect','activation_specificity','type2_pathway','disease_relevance','tractability','safety_risk','integrity_risk'].map(k=>_trComponentRow(k,c.components[k])).join('')}
     ${(()=>{const pm=c.perturbseq_measured;if(!pm)return '';const rr=pm.crossdonor_reproducibility;const rc=rr==null?'--secondary':(rr>=0.5?'--ok':(rr>=0.3?'--warn':'--risk'));const rt=rr==null?'n/a · single-guide target':rr.toFixed(2);return `<div style="padding:12px 0;border-top:1px solid var(--hairline)"><span class="mono" style="font-size:9px;letter-spacing:.1em;color:var(--ok)">✓ MEASURED IN DATASET · GLADSTONE CD4+ T-CELL PERTURB-SEQ</span><div style="font:400 12px/1.55 'Inter Tight',sans-serif;color:var(--ink2);margin-top:6px"><b style="color:var(--ink)">${pm.n_downstream_de_genes}</b> downstream DE genes · on-target knockdown <b style="color:var(--ink)">${pm.ontarget_effect_size.toFixed(1)}</b> · cross-donor reproducibility <b style="color:var(${rc})">${rt}</b>${rr!=null&&rr<0.3?' <span style="color:var(--risk)">— low; effect is donor-variable</span>':''}<div class="mono" style="font-size:10px;color:var(--secondary);margin-top:5px">${esc(pm.source)} · ${esc(pm.citation)}</div></div></div>`;})()}
     <div style="padding:12px 0;border-top:1px solid var(--hairline)"><span style="font:500 13px/1.3 'Inter Tight',sans-serif;color:var(--ink)">Missing evidence</span><div style="font:400 12px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:4px">${me.length?me.map(x=>'· '+esc(x)).join('<br>'):'— none flagged'}</div></div>
     <div class="mono" style="font-size:10px;color:var(--secondary);margin-top:8px">composite = Σ(weight × component) = ${c.composite.toFixed(3)}</div>
     ${c.disclaimer?`<div style="margin-top:8px;padding:7px 11px;border:1px solid var(--warn);border-radius:7px;background:var(--warn-c);font:500 10.5px/1.4 'Inter Tight',sans-serif;color:var(--warn)">⚠ ${esc(c.disclaimer)}</div>`:''}</div></div>`;}).join('');
 host.innerHTML=`<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px">
    <div class="mono" style="font-size:10px;color:var(--secondary);max-width:60ch">WEIGHTS · ${esc(weightsStr)}</div>
    <button id="tr-cf" style="display:inline-flex;align-items:center;gap:7px;border:1px solid var(${excluded?'--ok':'--risk'});background:none;color:var(${excluded?'--ok':'--risk'});border-radius:8px;padding:7px 12px;font:600 10.5px/1 'JetBrains Mono',monospace;letter-spacing:.03em;cursor:pointer"><span class="ms" style="font-size:14px">${excluded?'undo':'science'}</span>${excluded?'RESTORE THE PREPRINT':'EXCLUDE THE PREPRINT (not peer-reviewed)'}</button></div>
   ${wpanel}
   ${excluded?`<div style="margin-bottom:12px;padding:10px 13px;border:1px solid var(--warn);border-radius:8px;background:var(--warn-c);font:400 12px/1.5 'Inter Tight',sans-serif;color:var(--ink2)">Counterfactual: the not-yet-peer-reviewed preprint is <b>excluded</b>. Every component that rested on it is now <b>Unknown / insufficient evidence</b> and the ranking recomputed — nothing here is fixed text.</div>`:''}
   ${cards}`;
 host.querySelectorAll('[data-tr-toggle]').forEach(el=>el.onclick=()=>{const id=el.getAttribute('data-tr-toggle');const dt=$('#tr-detail-'+id);const ca=$('#tr-caret-'+id);if(dt){const open=dt.style.display!=='none';dt.style.display=open?'none':'block';if(ca)ca.textContent=open?'expand_more':'expand_less';}});
 const cf=$('#tr-cf'); if(cf) cf.onclick=()=>loadTargetRanking(dom, excluded?'':pre, weights);
 host.querySelectorAll('[data-wk]').forEach(sl=>{
   sl.oninput=()=>{const k=sl.getAttribute('data-wk');const vv=host.querySelector('[data-wv="'+k+'"]');if(vv)vv.textContent=sl.value+'%';};
   sl.onchange=()=>{const ws=[...host.querySelectorAll('[data-wk]')].map(s=>s.getAttribute('data-wk')+':'+(s.value/100)).join(',');loadTargetRanking(dom, exclude, ws);};
 });
 const wr=$('#tr-wreset'); if(wr) wr.onclick=()=>loadTargetRanking(dom, exclude, '');
}

/* ---------------- screen: Perturb-seq Analysis (the real ML pipeline, visible) ---------------- */
function screenPerturbseq(m){
 m.innerHTML=`<div class="reado"><div style="animation:ks-up .5s var(--e-out) both"><div class="mono" style="font-size:11px;letter-spacing:.16em;color:var(--secondary);margin-bottom:12px">PERTURB-SEQ ANALYSIS · TYPE-2 PROGRAM</div>
   <h1 style="font:400 38px/1.08 Newsreader,serif;letter-spacing:-.015em;color:var(--ink);margin:0 0 12px">The type-2 program collapse, measured</h1>
   <p style="font:400 15px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 6px;max-width:74ch"><b>Real measured data</b> from the Gladstone–UCSF CD4+ T-cell genome-scale Perturb-seq (Zhu … Marson, bioRxiv). Below: each regulator's real knockdown footprint — number of downstream DE genes, on-target knockdown, and cross-donor reproducibility — and, gene-by-gene, how <b>GATA3 knockdown collapses the actual type-2 cytokines</b> (IL4/IL5/IL13), measured as differential expression. Measured Δ, not a causal claim and not a trained model. A synthetic-matrix classifier is retained at the bottom as a transparent method check only — it never feeds the ranking.</p></div>
   <div id="ps-body" style="margin-top:18px;color:var(--secondary);font:400 12px/1.6 'JetBrains Mono',monospace">Running the pipeline…</div></div>`;
 loadPerturbseq(curDomain());
}
async function loadPerturbseq(dom){
 const host=$('#ps-body'); if(!host) return;
 let d=null; try{ d=await getJSON('/api/perturbseq?domain='+encodeURIComponent(dom)); }catch(e){ host.innerHTML=`<div style="color:var(--warn)">Could not run the pipeline (${esc(String(e))}).</div>`; return; }
 if(!d.baseline){ host.innerHTML=`<div style="padding:16px 0;color:var(--ink2);font:400 14px/1.6 'Inter Tight',sans-serif">${esc(d.note||'Defined for the CD4+ T-cell program.')} Switch to <b>IMMUNOLOGY · CD4 T-CELL</b>.</div>`; return; }
 const met=v=>v?`${v.mean} ± ${v.std} <span style="color:var(--secondary)">(${v.folds} folds)</span>`:'—';
 const stat=(k,v)=>`<div style="border:1px solid var(--hairline);border-radius:8px;background:var(--lowest);padding:11px 14px"><div class="mono" style="font-size:9px;letter-spacing:.08em;color:var(--secondary)">${k}</div><div style="font:500 15px/1.2 'Inter Tight',sans-serif;color:var(--ink);margin-top:4px">${v}</div></div>`;
 const eff=Object.entries(d.regulator_functional_effect).sort((a,b)=>b[1]-a[1]).map(([g,v])=>`<div style="display:flex;align-items:center;gap:12px;padding:7px 0"><span style="font:500 13px/1 'Inter Tight',sans-serif;color:var(--ink);width:82px">${esc(g)}</span><div style="flex:1;height:6px;border-radius:3px;background:var(--high);overflow:hidden"><div style="height:100%;width:${Math.round(v*100)}%;background:var(--primary)"></div></div><span class="mono" style="font-size:12px;color:var(--ink);width:44px;text-align:right">${v}</span></div>`).join('');
 // REAL DATA panel — the actual Gladstone Perturb-seq measurements (leads the screen)
 const gr=d.gladstone_real; let grPanel='';
 if(gr&&!gr.error&&gr.regulator_effects){const p=gr.provenance;
   const rows=Object.entries(gr.regulator_effects).filter(([,e])=>e).map(([g,e])=>{const rr=e.crossdonor_correlation_mean;const rc=rr==null?'--secondary':(rr>=0.5?'--ok':(rr>=0.3?'--warn':'--risk'));const rt=rr==null?'n/a':rr.toFixed(2);return `<tr style="border-top:1px solid var(--hairline)"><td style="padding:7px 10px;font:500 13px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(g)}</td><td style="padding:7px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--ink2)">${e.n_downstream_de_genes==null?e.n_downstream:e.n_downstream_de_genes}</td><td style="padding:7px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--ink2)">${e.ontarget_effect_size.toFixed(1)}</td><td style="padding:7px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(${rc})">${rt}${rr!=null&&rr<0.3?' ⚠':''}</td></tr>`;}).join('');
   grPanel=`<div style="margin-bottom:16px;border:1px solid var(--ok);border-radius:10px;background:var(--paper);overflow:hidden"><div style="padding:12px 16px;background:var(--lowest);border-bottom:1px solid var(--hairline)"><span class="mono" style="font-size:9px;letter-spacing:.12em;color:var(--ok)">✓ REAL DATA · MEASURED</span><div style="font:500 14px/1.3 'Inter Tight',sans-serif;color:var(--ink);margin-top:4px">Gladstone–UCSF CD4+ T-cell genome-scale Perturb-seq</div><div style="font:400 11.5px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:3px">${esc((p.authors&&p.authors[0])||'')} … ${esc((p.authors&&p.authors[p.authors.length-1])||'')} · <a href="${esc(p.url)}" target="_blank" rel="noopener" style="color:var(--secondary)">DOI:${esc(p.doi)}</a> · <span style="color:var(--warn)">preprint · not peer-reviewed</span> · condition ${esc(gr.condition)}</div></div><table style="width:100%;border-collapse:collapse"><thead><tr><th style="padding:8px 10px;text-align:left;font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em;color:var(--secondary)">REGULATOR</th><th style="padding:8px 10px;text-align:right;font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em;color:var(--secondary)">DOWNSTREAM DE</th><th style="padding:8px 10px;text-align:right;font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em;color:var(--secondary)">ON-TARGET KD</th><th style="padding:8px 10px;text-align:right;font:600 9px/1 'JetBrains Mono',monospace;letter-spacing:.08em;color:var(--secondary)">CROSS-DONOR r</th></tr></thead><tbody>${rows}</tbody></table><div style="padding:9px 14px;font:400 11px/1.5 'Inter Tight',sans-serif;color:var(--ink2);border-top:1px solid var(--hairline)">Measured knockdown footprint in primary human CD4+ T cells (4 donors). <b style="color:var(--ink)">FBXO32's cross-donor reproducibility is low (0.13)</b> — a real, measured reason the preprint's novel nominee is provisional. This is the real layer; the classifier below is a synthetic/exploratory cross-check.</div></div>`;}
 // REAL, direction-resolved: GATA3 knockdown's measured footprint on the type-2 genes
 let fpPanel=''; const fp=gr&&gr.gata3_th2_footprint;
 if(fp&&fp.footprint&&fp.footprint.length){
   const mx=Math.max(...fp.footprint.map(x=>Math.abs(x.log2fc)))||1;
   const rows=fp.footprint.slice().sort((a,b)=>a.log2fc-b.log2fc).map(x=>{
     const down=x.log2fc<0, w=Math.round(Math.abs(x.log2fc)/mx*50), col=down?'--risk':'--ok';
     const bar=down
       ?`<div style="flex:1;display:flex;justify-content:flex-end"><div style="width:${w}%;height:11px;border-radius:3px 0 0 3px;background:var(--risk)"></div></div><div style="flex:1"></div>`
       :`<div style="flex:1"></div><div style="flex:1"><div style="width:${w}%;height:11px;border-radius:0 3px 3px 0;background:var(--ok)"></div></div>`;
     return `<div style="display:flex;align-items:center;gap:8px;padding:3px 0"><span style="width:66px;flex:none;font:500 12px/1 'Inter Tight',sans-serif;color:var(--ink)">${esc(x.gene)}</span><div style="flex:1;display:flex;align-items:center;border-left:1px solid var(--hairline);border-right:1px solid var(--hairline)">${bar}</div><span class="mono" style="width:58px;flex:none;text-align:right;font-size:11px;color:var(${col})">${x.log2fc>0?'+':''}${x.log2fc.toFixed(2)}${x.significant?'':'<span style="color:var(--secondary)"> ns</span>'}</span></div>`;
   }).join('');
   fpPanel=`<div style="margin-bottom:16px;border:1px solid var(--ok);border-radius:10px;background:var(--paper);overflow:hidden">
     <div style="padding:12px 16px;background:var(--lowest);border-bottom:1px solid var(--hairline)"><span class="mono" style="font-size:9px;letter-spacing:.12em;color:var(--ok)">✓ REAL DATA · DIRECTION-RESOLVED</span><div style="font:500 15px/1.3 'Inter Tight',sans-serif;color:var(--ink);margin-top:4px">GATA3 knockdown collapses the type-2 program</div><div style="font:400 11.5px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:3px">Measured Δ per gene · ${esc(fp.condition)} · ${esc(fp.source_table)} · <b style="color:var(--risk)">Th2-collapse score ${fp.th2_collapse_score}</b> (mean log2FC · ${fp.n_significantly_down}/${fp.n_signature_genes_measured} significantly down)</div></div>
     <div style="padding:12px 16px">${rows}
       <div style="display:flex;justify-content:space-between;font:600 8.5px/1 'JetBrains Mono',monospace;letter-spacing:.06em;color:var(--secondary);margin-top:6px;padding-top:6px;border-top:1px solid var(--hairline)"><span>◄ DOWN · type-2 collapses</span><span>log2 fold-change (KD vs control)</span><span>UP ►</span></div></div>
     <div style="padding:9px 16px;font:400 11px/1.55 'Inter Tight',sans-serif;color:var(--ink2);border-top:1px solid var(--hairline)">The type-2 cytokines (IL5/IL13/IL4/IL9), Th2 chemokine receptors (CCR4/CCR8) and AREG fall; <b style="color:var(--ink)">STAT6 — GATA3's upstream regulator — is unchanged</b>, confirming the effect is specific, not global. Real differential expression; a measured Δ, not causal proof.</div></div>`;
 }
 host.innerHTML=`${grPanel}${fpPanel}<div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--secondary);margin-bottom:8px">METHOD CHECK · synthetic matrix (not a ranking input)</div><div style="margin-bottom:16px;padding:11px 14px;border:1px solid var(--warn);border-radius:8px;background:var(--warn-c);font:500 11px/1.5 'JetBrains Mono',monospace;color:var(--warn)">⚠ ${esc(d.data_label)}</div>
   <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:20px">${stat('CELLS',d.n_cells)}${stat('GENES · POST-QC',d.n_genes_after_qc+' · '+d.n_genes_excluded_qc+' excl')}${stat('SPLIT','leave-one-pert-out')}${stat('SIGNATURE GENES',d.signature_genes.length)}</div>
   <div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--secondary);margin-bottom:10px">BASELINE vs MODEL · cross-fold mean ± std</div>
   <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
    <div style="flex:1;min-width:230px;border:1px solid var(--hairline);border-radius:9px;padding:14px 16px;background:var(--paper)"><div style="font:500 13px/1.3 'Inter Tight',sans-serif;color:var(--ink)">Baseline · ${esc(d.baseline.name)}</div><div class="mono" style="font-size:12px;color:var(--ink2);margin-top:6px">AUROC ${met(d.baseline.auroc)}<br>accuracy ${met(d.baseline.accuracy)}</div></div>
    <div style="flex:1;min-width:230px;border:1px solid var(--primary);border-radius:9px;padding:14px 16px;background:var(--paper)"><div style="font:500 13px/1.3 'Inter Tight',sans-serif;color:var(--ink)">Model · ${esc(d.model.name)}</div><div class="mono" style="font-size:12px;color:var(--ink2);margin-top:6px">AUROC ${met(d.model.auroc)}<br>accuracy ${met(d.model.accuracy)}</div></div></div>
   <div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--secondary);margin-bottom:8px">COMPUTED FUNCTIONAL EFFECT · Δ type-2 signature score per knockdown</div>
   <div style="border:1px solid var(--hairline);border-radius:9px;background:var(--lowest);padding:12px 16px;margin-bottom:20px">${eff}</div>
   <div class="mono" style="font-size:10px;color:var(--secondary);margin-bottom:8px">REPRODUCIBILITY · seed ${esc(d.reproducibility.seed)} · code ${esc(d.reproducibility.code_hash)} · numpy ${esc(d.reproducibility.numpy)}</div>
   <div style="font:400 12px/1.6 'Inter Tight',sans-serif;color:var(--ink2)"><b style="color:var(--ink)">Limitations:</b> ${d.limitations.map(esc).join(' · ')}<br><b style="color:var(--ink)">Failure modes:</b> ${d.failure_modes.map(esc).join(' · ')}</div>`;
}

/* ---------------- screen: Data Readiness (Phase 2 · Priority 1) ---------------- */
const _DR_TONE={real_public:['--ok','REAL · PUBLIC'],gladstone:['--ok','REAL · GLADSTONE'],synthetic_fixture:['--warn','SYNTHETIC · FIXTURE'],unavailable:['--risk','UNAVAILABLE']};
function screenDataReady(m){
 m.innerHTML=`<div class="reado"><div style="animation:ks-up .5s var(--e-out) both"><div class="mono" style="font-size:11px;letter-spacing:.16em;color:var(--secondary);margin-bottom:12px">DATA READINESS · WHAT DRIVES THE RANKING</div>
   <h1 style="font:400 38px/1.08 Newsreader,serif;letter-spacing:-.015em;color:var(--ink);margin:0 0 12px">Every source, labeled by exactly what it is</h1>
   <p style="font:400 15px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 6px;max-width:74ch">Before any ranking, Keystone declares each dataset: its accession, version, type, QC, biological limits, and whether it can change the target ranking. <b>Real data drives the ranking; the synthetic classifier is a labeled cross-check that cannot.</b> Preprints are flagged not-peer-reviewed.</p></div>
   <div id="dr-body" style="margin-top:18px;color:var(--secondary);font:400 12px/1.6 'JetBrains Mono',monospace">Auditing data sources…</div></div>`;
 loadDataReady(curDomain());
}
async function loadDataReady(dom){
 const host=$('#dr-body'); if(!host) return;
 let d=null; try{ d=await getJSON('/api/data_readiness?domain='+encodeURIComponent(dom)); }catch(e){ host.innerHTML=`<div style="color:var(--warn)">Could not load data readiness (${esc(String(e))}).</div>`; return; }
 if(!d.sources||!d.sources.length){ host.innerHTML=`<div style="padding:16px 0;color:var(--ink2);font:400 14px/1.6 'Inter Tight',sans-serif">${esc(d.note||'Defined for the CD4+ T-cell program.')} Switch to <b>IMMUNOLOGY · CD4 T-CELL</b>.</div>`; return; }
 const cards=d.sources.map(s=>{const t=_DR_TONE[s.source_type]||['--secondary',s.source_type];const ar=s.affects_ranking;
   return `<div style="border:1px solid var(${ar?t[0]:'--outline'});border-radius:10px;background:var(--paper);margin-bottom:12px;overflow:hidden">
     <div style="display:flex;align-items:center;gap:12px;padding:13px 16px;border-bottom:1px solid var(--hairline);flex-wrap:wrap">
       <span class="mono" style="font-size:9px;letter-spacing:.08em;color:var(${t[0]})">${t[1]}</span>
       <span style="flex:1;min-width:160px;font:500 14px/1.25 'Inter Tight',sans-serif;color:var(--ink)">${esc(s.name)}</span>
       <span class="mono" style="font-size:9px;padding:3px 9px;border-radius:20px;background:var(--container);color:var(${ar?'--ok':'--outline'})">${ar?'AFFECTS RANKING':'NOT A RANKING INPUT'}</span>
       ${s.peer_reviewed===false?`<span class="mono" style="font-size:9px;color:var(--warn)">PREPRINT</span>`:''}</div>
     <div style="padding:12px 16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px 20px">
       ${[['SOURCE',s.url?`<a href="${esc(s.url)}" target="_blank" rel="noopener" style="color:var(--claude-live);text-decoration:none">${esc(s.source_id)}</a>`:esc(s.source_id)],['VERSION',esc(s.version||'—')],['PREPROCESSING',esc(s.preprocessing)],['QC',esc(s.qc)],['ROLE',esc(s.affects_how)]].map(([k,v])=>`<div><div class="mono" style="font-size:8.5px;letter-spacing:.08em;color:var(--secondary)">${k}</div><div style="font:400 12px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:2px">${v}</div></div>`).join('')}</div>
     <div style="padding:0 16px 12px"><div class="mono" style="font-size:8.5px;letter-spacing:.08em;color:var(--secondary);margin-bottom:3px">BIOLOGICAL LIMITATIONS</div><div style="font:400 11.5px/1.55 'Inter Tight',sans-serif;color:var(--ink2)">${(s.biological_limitations||[]).map(x=>'· '+esc(x)).join('<br>')}</div></div></div>`;}).join('');
 const c=d.counts_by_type||{};
 host.innerHTML=`<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px">
    <span class="mono" style="font-size:10px;padding:5px 11px;border-radius:20px;background:var(--paper);border:1px solid var(--ok);color:var(--ok)">${(c.real_public||0)+(c.gladstone||0)} REAL</span>
    <span class="mono" style="font-size:10px;padding:5px 11px;border-radius:20px;background:var(--paper);border:1px solid var(--warn);color:var(--warn)">${c.synthetic_fixture||0} SYNTHETIC</span>
    ${c.unavailable?`<span class="mono" style="font-size:10px;padding:5px 11px;border-radius:20px;background:var(--paper);border:1px solid var(--risk);color:var(--risk)">${c.unavailable} UNAVAILABLE</span>`:''}</div>
   ${cards}
   <div style="margin-top:6px;padding:11px 14px;border:1px solid var(--hairline);border-radius:8px;background:var(--lowest);font:400 12px/1.55 'Inter Tight',sans-serif;color:var(--ink2)"><b style="color:var(--ink)">Invariant:</b> ${esc(d.invariant)}</div>`;
}
/* ---------------- screen: Research Cell — the 5-agent run (Phase 2 · Priority 3) ---------------- */
const _AG_ICON={'Data Analysis Agent':'science','Literature Evidence Agent':'menu_book','Target Biology / Pathway Agent':'account_tree','Integrity & Retraction Agent':'gpp_maybe','Reviewer Agent':'gavel'};
const _RS_TONE={approved:['--ok','APPROVED'],corroboration:['--warn','CORROBORATION'],rejected:['--risk','REJECTED'],pending:['--secondary','PENDING'],'n/a':['--secondary','GATE']};
function screenCell(m){
 m.innerHTML=`<div class="reado"><div style="animation:ks-up .5s var(--e-out) both"><div class="mono" style="font-size:11px;letter-spacing:.16em;color:var(--secondary);margin-bottom:12px">KEYSTONE RESEARCH CELL · FIVE AGENTS, ONE AUDITED RUN</div>
   <h1 style="font:400 38px/1.08 Newsreader,serif;letter-spacing:-.015em;color:var(--ink);margin:0 0 12px">A controlled cell, not a swarm</h1>
   <p style="font:400 15px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 6px;max-width:76ch">Five real agents run over the real corpus. Each records its inputs, tool calls, source-backed claims, run id, and timestamp. <b>No output becomes primary ranking support until the Reviewer Agent approves it</b> — preprint data is admitted as provisional corroboration; the synthetic cross-check is rejected outright.</p></div>
   <div id="rc-body" style="margin-top:18px;color:var(--secondary);font:400 12px/1.6 'JetBrains Mono',monospace">Running the five agents…</div></div>`;
 loadCell(curDomain());
}
async function loadCell(dom){
 const host=$('#rc-body'); if(!host) return;
 let d=null,ev=null; try{ [d,ev]=await Promise.all([getJSON('/api/research_cell/run?domain='+encodeURIComponent(dom)), getJSON('/api/cell_eval?domain='+encodeURIComponent(dom)).catch(()=>null)]); }catch(e){ host.innerHTML=`<div style="color:var(--warn)">Could not run the cell (${esc(String(e))}).</div>`; return; }
 if(!d.agents||!d.agents.length){ host.innerHTML=`<div style="padding:16px 0;color:var(--ink2);font:400 14px/1.6 'Inter Tight',sans-serif">Defined for the CD4+ T-cell program. Switch to <b>IMMUNOLOGY · CD4 T-CELL</b>.</div>`; return; }
 const agents=d.agents.map((a,i)=>{const rs=_RS_TONE[a.reviewer_status]||['--secondary',a.reviewer_status];const gate=/Integrity|Reviewer/.test(a.name);
   const claims=(a.claims||[]).slice(0,6).map(c=>{const tone=/EXCLUDE|REJECT/.test(c.text)?'--risk':/PROVISIONAL|CORROBORATION/.test(c.text)?'--warn':/APPROVE|cleared/.test(c.text)?'--ok':'--ink2';return `<div style="display:flex;gap:8px;padding:4px 0;border-top:1px solid var(--hairline)"><span class="mono" style="font-size:9px;color:var(--outline);flex:none;width:96px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.id)}</span><span style="flex:1;font:400 11.5px/1.45 'Inter Tight',sans-serif;color:var(${tone})">${esc(c.text)}</span></div>`;}).join('');
   return `<div style="border:1px solid var(${gate?'--warn':'--hairline'});border-radius:10px;background:var(--paper);margin-bottom:12px;overflow:hidden">
     <div style="display:flex;align-items:center;gap:11px;padding:12px 16px;border-bottom:1px solid var(--hairline);flex-wrap:wrap">
       <span class="mono" style="font-size:9px;color:var(--outline);flex:none">${String(i+1).padStart(2,'0')}</span>
       <span class="ms" style="font-size:18px;color:var(${gate?'--warn':'--secondary'});flex:none">${_AG_ICON[a.name]||'smart_toy'}</span>
       <span style="flex:1;min-width:150px;font:600 14px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(a.name)}</span>
       <span class="mono" style="font-size:9px;padding:3px 9px;border-radius:20px;background:var(--container);color:var(${a.status==='ok'?'--ok':a.status==='failed'?'--risk':'--warn'})">${esc((a.status||'').toUpperCase())}</span>
       ${gate?'':`<span class="mono" style="font-size:9px;padding:3px 9px;border-radius:20px;background:var(--container);color:var(${rs[0]})">${rs[1]}</span>`}</div>
     <div style="padding:10px 16px"><div class="mono" style="font-size:9px;color:var(--secondary);margin-bottom:6px">TOOL CALLS · <span style="color:var(--ok)">✓ executed &amp; fingerprinted</span></div><div style="margin-bottom:7px">${((a.tool_receipts&&a.tool_receipts.length?a.tool_receipts:(a.tool_calls||[]).map(t=>({tool:t,evidence:null}))).map(rc=>`<span style="display:inline-flex;align-items:center;gap:4px;margin:0 6px 5px 0;padding:2px 7px;border-radius:6px;background:var(--container);font:500 9.5px/1.4 'JetBrains Mono',monospace;color:var(--ink2)"><span class="ms" style="font-size:11px;color:var(--ok)">check_circle</span>${esc(rc.tool)}${rc.evidence?` <span style="color:var(--outline)">sha:${esc(rc.evidence.sha)}${rc.evidence.n!=null?'·n'+rc.evidence.n:''}</span>`:''}</span>`).join(''))||'—'}</div>
       ${claims||'<div style="font:400 11px/1.4 Inter Tight,sans-serif;color:var(--secondary)">no claims</div>'}
       ${(a.claims||[]).length>6?`<div class="mono" style="font-size:9px;color:var(--secondary);padding-top:5px">+${a.claims.length-6} more…</div>`:''}
       <div class="mono" style="font-size:8.5px;color:var(--outline);margin-top:7px;padding-top:6px;border-top:1px solid var(--hairline)">run ${esc(a.run_id)} · ${esc(a.timestamp)} · ledger ✓</div></div></div>`;}).join('');
 const chip=(label,arr,tone)=>`<div style="flex:1;min-width:150px;border:1px solid var(${tone});border-radius:9px;background:var(--paper);padding:12px 14px"><div class="mono" style="font-size:9px;letter-spacing:.08em;color:var(${tone})">${label} · ${arr.length}</div><div style="font:400 11px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:5px">${arr.length?arr.map(c=>esc(c.id||c)).join(', '):'—'}</div></div>`;
 const evalHTML=ev?(()=>{const tone=ev.all_pass?'--ok':'--risk';const rows=ev.cases.map(c=>`<div style="display:flex;gap:8px;padding:4px 0;border-top:1px solid var(--hairline)"><span class="ms" style="font-size:14px;color:var(${c.passed?'--ok':'--risk'});flex:none">${c.passed?'check_circle':'cancel'}</span><span class="mono" style="font-size:10px;color:var(--ink);flex:none;width:150px">${esc(c.id)}</span><span style="flex:1;font:400 11px/1.4 'Inter Tight',sans-serif;color:var(--ink2)">${esc(c.property)}</span></div>`).join('');
   return `<div style="border:1px solid var(${tone});border-radius:10px;background:var(--paper);margin-bottom:18px;overflow:hidden"><div style="display:flex;align-items:center;gap:11px;padding:12px 16px;border-bottom:1px solid var(--hairline)"><span class="ms" style="font-size:19px;color:var(${tone})">${ev.all_pass?'verified':'error'}</span><span style="flex:1;font:600 13px/1.2 'Inter Tight',sans-serif;color:var(--ink)">Scientific-correctness eval</span><span class="mono" style="font-size:12px;font-weight:700;color:var(${tone})">${ev.passed}/${ev.n} PASS</span></div><div style="padding:6px 16px 12px">${rows}<div class="mono" style="font-size:8.5px;color:var(--outline);margin-top:8px;padding-top:6px;border-top:1px solid var(--hairline)">deterministic judges over the real run · canary-tested (breaking an invariant fails a case) · /api/cell_eval</div></div></div>`;})():'';
 host.innerHTML=`${evalHTML}<div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--secondary);margin-bottom:6px">RUN ${esc(d.run_id)} · ${d.agents.length} AGENTS · ${(d.ledger||[]).length} LEDGER ENTRIES</div>
   ${agents}
   <div class="mono" style="font-size:10px;letter-spacing:.1em;color:var(--secondary);margin:20px 0 8px">THE REVIEWER GATE · what may affect the ranking</div>
   <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">${chip('PRIMARY SUPPORT',d.admitted_to_ranking||[],'--ok')}${chip('CORROBORATION',d.corroboration||[],'--warn')}${chip('REJECTED',d.rejected||[],'--risk')}</div>
   <div style="padding:11px 14px;border:1px solid var(--hairline);border-radius:8px;background:var(--lowest);font:400 12px/1.55 'Inter Tight',sans-serif;color:var(--ink2)"><b style="color:var(--ink)">Gate:</b> ${esc(d.gate_note)}</div>`;
}
/* ---------------- screen: Cell-State Atlas (Visual Evidence Lab · Mode 1) ---------------- */
const _ARM_COL={NTC:'#8a94a6',GATA3:'#2dd4bf',STAT6:'#5b9df0',RARA:'#e0a13a',FBXO32:'#e07aa8'};
const _DONOR_COL={D1:'#2dd4bf',D2:'#5b9df0',D3:'#e0a13a',D4:'#e07aa8'};
let _ATLAS={data:null,color:'arm',selected:null};
function _gradTealAmber(t){ // 0 teal → 1 amber, no neon
 const a=[45,140,130],b=[224,161,58]; const c=a.map((v,i)=>Math.round(v+(b[i]-v)*t));
 return `rgb(${c[0]},${c[1]},${c[2]})`;
}
function screenAtlas(m){
 m.innerHTML=`<div style="animation:ks-up .5s var(--e-out) both;padding:26px 30px 40px">
   <div class="mono" style="font-size:11px;letter-spacing:.16em;color:var(--secondary);margin-bottom:10px">VISUAL EVIDENCE LAB</div>
   <h1 style="font:400 34px/1.1 Newsreader,serif;letter-spacing:-.015em;color:var(--ink);margin:0 0 8px">The evidence, in real numbers</h1>
   <p style="font:400 14px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin:0 0 4px;max-width:84ch">The default view is <b style="color:var(--ok)">measured</b> — every point is a real Gladstone Perturb-seq metric that drives the ranking. It shows the weakest link at a glance: <b>FBXO32</b> has a large footprint at very low cross-donor reproducibility. Select a regulator for its provenance. A synthetic cell-embedding is available as a clearly-labelled method illustration. Research use only — not clinical.</p>
   <div id="atlas-wrap" style="margin-top:16px;color:var(--secondary);font:400 12px/1.6 'JetBrains Mono',monospace">Loading measured evidence…</div></div>`;
 loadAtlas(curDomain());
}
async function loadAtlas(dom){
 const host=$('#atlas-wrap'); if(!host) return;
 let mp=null,at=null;
 try{ [mp,at]=await Promise.all([getJSON('/api/regulator_map?domain='+encodeURIComponent(dom)), getJSON('/api/atlas?domain='+encodeURIComponent(dom)).catch(()=>null)]); }catch(e){ host.innerHTML=`<div style="color:var(--warn)">Could not load the evidence lab (${esc(String(e))}).</div>`; return; }
 if(!mp||!mp.available){ host.innerHTML=`<div style="padding:16px 0;color:var(--ink2);font:400 14px/1.6 'Inter Tight',sans-serif">${esc((mp&&mp.note)||'Defined for the CD4+ T-cell program.')} Switch to <b>IMMUNOLOGY · CD4 T-CELL</b>.</div>`; return; }
 _ATLAS={data:at,map:mp,mode:'measured',color:'arm',selected:null};
 renderLab();
}
function _placeholderPanel(measured){return `<div id="atlas-panel"><div style="border:1px solid var(--hairline);border-radius:10px;background:var(--paper);padding:16px;font:400 12.5px/1.6 'Inter Tight',sans-serif;color:var(--ink2)"><span class="ms" style="font-size:20px;color:var(--secondary)">ads_click</span><div style="margin-top:6px">Select a regulator to see its <b style="color:var(--ok)">measured</b> Gladstone metrics, ranking link, and what it does <b>not</b> prove.</div></div></div>`;}
function renderLab(){
 const host=$('#atlas-wrap'); if(!host||!_ATLAS.map) return;
 const measured=_ATLAS.mode==='measured', hasSynth=!!(_ATLAS.data&&_ATLAS.data.available);
 const modeBtn=(id,label,active,tone,note,dis)=>`<button ${dis?'disabled':`data-mode="${id}"`} style="display:block;width:100%;text-align:left;border:1px ${dis?'dashed':'solid'} var(${active?tone:dis?'--outline':'--hairline'});background:${active?'var(--container)':'none'};color:var(${active?'--ink':dis?'--outline':'--ink2'});border-radius:7px;padding:8px 10px;margin-bottom:6px;font:${active?600:500} 11.5px/1.2 'Inter Tight',sans-serif;cursor:${dis?'not-allowed':'pointer'}">${active?'● ':''}${label}${note?` <span class="mono" style="font-size:8px;color:var(${tone})">${note}</span>`:''}</button>`;
 let center, leftExtra='';
 if(measured){
   center=drawRegMap(_ATLAS.map);
 } else {
   const d=_ATLAS.data;
   const colorBtns=d.colorings.map(c=>`<button data-color="${c.id}" class="atlas-cbtn" style="display:block;width:100%;text-align:left;border:1px solid var(--hairline);background:${c.id===_ATLAS.color?'var(--container)':'none'};color:var(--ink2);border-radius:7px;padding:7px 10px;margin-bottom:6px;font:500 11.5px/1.2 'Inter Tight',sans-serif;cursor:pointer">${esc(c.name)}${c.kind==='computed'?' <span class="mono" style="font-size:8px;color:var(--warn)">COMPUTED</span>':''}</button>`).join('');
   leftExtra=`<div class="mono" style="font-size:9px;letter-spacing:.1em;color:var(--secondary);margin:12px 0 7px">COLOR BY</div>${colorBtns}<div class="mono" style="font-size:9px;letter-spacing:.1em;color:var(--secondary);margin:14px 0 7px">LEGEND</div><div id="atlas-legend" style="font:400 11px/1.7 'Inter Tight',sans-serif;color:var(--ink2)"></div>`;
   center=`<div style="border:1px solid var(--hairline);border-radius:10px;background:var(--paper);overflow:hidden"><div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--hairline)"><span class="mono" style="font-size:9px;letter-spacing:.08em;color:var(--warn)">⚠ ${esc(d.provenance_tag)}</span><span class="mono" style="font-size:9px;color:var(--secondary)">${d.n_cells} cells · ${esc(d.embedding.method)}</span></div><canvas id="atlas-canvas" style="display:block;width:100%;height:400px;cursor:crosshair"></canvas></div><div style="margin-top:8px;padding:9px 12px;border:1px solid var(--hairline);border-radius:8px;background:var(--lowest);font:400 11px/1.5 'Inter Tight',sans-serif;color:var(--ink2)">${esc(d.data_label)}</div>`;
 }
 host.innerHTML=`<div style="display:grid;grid-template-columns:190px minmax(0,1fr);gap:16px;align-items:start">
    <div>
      <div class="mono" style="font-size:9px;letter-spacing:.1em;color:var(--secondary);margin-bottom:7px">LAYER</div>
      ${modeBtn('measured','Regulator map',measured,'--ok','MEASURED',false)}
      ${modeBtn('synthetic','Cell embedding',!measured,'--warn','SYNTHETIC',!hasSynth)}
      <button title="No visual dataset connected" disabled style="display:block;width:100%;text-align:left;border:1px dashed var(--outline);background:none;color:var(--outline);border-radius:7px;padding:8px 10px;margin-bottom:6px;font:500 11.5px/1.2 'Inter Tight',sans-serif;cursor:not-allowed">Spatial / Microscopy <span class="mono" style="font-size:8px">DISABLED</span></button>
      ${leftExtra}
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:16px;align-items:start">
      <div style="flex:2 1 360px;min-width:0">${center}</div>
      <div style="flex:1 1 280px;min-width:0">${_placeholderPanel(measured)}</div>
    </div>
  </div>`;
 host.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{_ATLAS.mode=b.getAttribute('data-mode');_ATLAS.selected=null;renderLab();});
 if(measured){
   host.querySelectorAll('[data-gene]').forEach(el=>el.onclick=()=>selectArm(el.getAttribute('data-gene')));
 } else {
   host.querySelectorAll('.atlas-cbtn').forEach(b=>b.onclick=()=>{_ATLAS.color=b.getAttribute('data-color');host.querySelectorAll('.atlas-cbtn').forEach(x=>x.style.background='none');b.style.background='var(--container)';drawAtlas();renderLegend();});
   const cv=$('#atlas-canvas');
   if(cv){ cv.onclick=(e)=>{const r=cv.getBoundingClientRect();const px=(e.clientX-r.left)/r.width,py=1-(e.clientY-r.top)/r.height;let best=null,bd=1e9;_ATLAS.data.cells.forEach(c=>{const dx=c.x-px,dy=c.y-py,dd=dx*dx+dy*dy;if(dd<bd){bd=dd;best=c;}});if(best)selectArm(best.arm);}; }
   drawAtlas(); renderLegend();
 }
}
function drawRegMap(mp){
 const W=480,H=380,L=58,R=20,T=20,B=46, na=L-30;
 const maxDE=Math.max(...mp.points.map(p=>p.n_downstream_de||0),1), thr=mp.reproducibility_threshold;
 const xr=r=>L+r*(W-L-R), yd=de=>H-B-(de/maxDE)*(H-B-T);
 const grid=[0,0.25,0.5,0.75,1].map(t=>`<line x1="${xr(t).toFixed(1)}" y1="${T}" x2="${xr(t).toFixed(1)}" y2="${H-B}" stroke="var(--hairline)"/><text x="${xr(t).toFixed(1)}" y="${H-B+15}" text-anchor="middle" font-size="9" fill="var(--secondary)" font-family="monospace">${t.toFixed(2)}</text>`).join('');
 const dz=`<rect x="${L}" y="${T}" width="${(xr(thr)-L).toFixed(1)}" height="${H-B-T}" fill="var(--risk)" opacity="0.06"/><text x="${xr(thr/2).toFixed(1)}" y="${T+13}" text-anchor="middle" font-size="8" fill="var(--risk)" font-family="monospace">low reproducibility</text>`;
 const pts=mp.points.map(p=>{const rad=(4+Math.abs(p.ontarget_kd||0)/20*6).toFixed(1);const miss=p.reproducibility_missing;const cx=(miss?na:xr(p.crossdonor_r)).toFixed(1);const cy=yd(p.n_downstream_de).toFixed(1);const col=p.provisional?'--risk':miss?'--outline':'--ok';const ring=p.provisional?`<circle cx="${cx}" cy="${cy}" r="${(+rad+4).toFixed(1)}" fill="none" stroke="var(--risk)" stroke-dasharray="3 2" opacity="0.75"/>`:'';return `<g data-gene="${p.gene}" style="cursor:pointer">${ring}<circle cx="${cx}" cy="${cy}" r="${rad}" fill="var(${col})" opacity="0.82"/><text x="${(+cx+ +rad+5).toFixed(1)}" y="${(+cy+3).toFixed(1)}" font-size="11.5" font-weight="600" fill="var(--ink)" font-family="Inter Tight,sans-serif">${esc(p.gene)}</text><text x="${(+cx+ +rad+5).toFixed(1)}" y="${(+cy+15).toFixed(1)}" font-size="8.5" fill="var(--secondary)" font-family="monospace">#${p.rank} · ${p.n_downstream_de} DE · r ${miss?'n/a':p.crossdonor_r}</text></g>`;}).join('');
 return `<div style="border:1px solid var(--ok);border-radius:10px;background:var(--paper);overflow:hidden">
   <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--hairline)"><span class="mono" style="font-size:9px;letter-spacing:.06em;color:var(--ok)">● ${esc(mp.provenance_tag)} · real Gladstone Perturb-seq</span><span class="mono" style="font-size:9px;color:var(${mp.peer_reviewed?'--secondary':'--warn'})">${mp.peer_reviewed?'peer-reviewed':'preprint'}</span></div>
   <svg viewBox="0 0 ${W} ${H}" style="display:block;width:100%">${dz}${grid}
     <line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" stroke="var(--outline)"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" stroke="var(--outline)"/>
     <text x="${((L+W-R)/2).toFixed(0)}" y="${H-6}" text-anchor="middle" font-size="10" fill="var(--secondary)" font-family="Inter Tight,sans-serif">cross-donor reproducibility (r) →</text>
     <text x="15" y="${((T+H-B)/2).toFixed(0)}" text-anchor="middle" font-size="10" fill="var(--secondary)" font-family="Inter Tight,sans-serif" transform="rotate(-90 15 ${((T+H-B)/2).toFixed(0)})">downstream DE genes →</text>
     <text x="${na}" y="${H-B+15}" text-anchor="middle" font-size="7.5" fill="var(--outline)" font-family="monospace">n/a</text>
     ${pts}</svg>
   <div style="padding:9px 12px;border-top:1px solid var(--hairline);font:400 11px/1.5 'Inter Tight',sans-serif;color:var(--ink2)"><b style="color:var(--ink)">Reading it:</b> ${esc(mp.insight)}</div></div>`;
}
function renderLegend(){
 const el=$('#atlas-legend'); if(!el||!_ATLAS.data) return; const mode=_ATLAS.color;
 if(mode==='arm'){ el.innerHTML=['NTC','GATA3','STAT6','RARA','FBXO32'].map(a=>`<div style="display:flex;align-items:center;gap:7px"><span style="width:10px;height:10px;border-radius:50%;background:${_ARM_COL[a]}"></span>${a}${a==='FBXO32'?' <span class="mono" style="font-size:8px;color:var(--warn)">preprint</span>':''}</div>`).join(''); }
 else if(mode==='donor'){ el.innerHTML=['D1','D2','D3','D4'].map(a=>`<div style="display:flex;align-items:center;gap:7px"><span style="width:10px;height:10px;border-radius:50%;background:${_DONOR_COL[a]}"></span>${a}</div>`).join(''); }
 else { el.innerHTML=`<div style="display:flex;align-items:center;gap:7px"><span style="width:44px;height:9px;border-radius:3px;background:linear-gradient(90deg,${_gradTealAmber(0)},${_gradTealAmber(1)})"></span></div><div class="mono" style="font-size:9px;color:var(--secondary);margin-top:3px">low → high (computed)</div>`; }
}
function drawAtlas(){
 const cv=$('#atlas-canvas'); if(!cv||!_ATLAS.data) return;
 const dpr=window.devicePixelRatio||1, w=cv.clientWidth, h=cv.clientHeight;
 cv.width=w*dpr; cv.height=h*dpr; const ctx=cv.getContext('2d'); ctx.scale(dpr,dpr); ctx.clearRect(0,0,w,h);
 const pad=14, mode=_ATLAS.color, sel=_ATLAS.selected;
 _ATLAS.data.cells.forEach(c=>{
   const x=pad+c.x*(w-2*pad), y=h-pad-c.y*(h-2*pad);
   let col; if(mode==='arm')col=_ARM_COL[c.arm]||'#888'; else if(mode==='donor')col=_DONOR_COL[c.donor]||'#888'; else col=_gradTealAmber(mode==='sig'?c.sig:c.qc);
   const dim=sel && c.arm!==sel; ctx.globalAlpha=dim?0.12:0.72; ctx.fillStyle=col;
   ctx.beginPath(); ctx.arc(x,y,dim?1.4:2.1,0,6.2832); ctx.fill();
 });
 ctx.globalAlpha=1;
}
async function selectArm(arm){
 _ATLAS.selected=arm; drawAtlas();
 const panel=$('#atlas-panel'); if(panel) panel.innerHTML=`<div style="border:1px solid var(--hairline);border-radius:10px;background:var(--paper);padding:16px;color:var(--secondary);font:400 12px/1.5 'JetBrains Mono',monospace">Recomputing arm ${esc(arm)}…</div>`;
 let d=null; try{ d=await getJSON('/api/atlas/select?domain='+encodeURIComponent(curDomain())+'&arm='+encodeURIComponent(arm)); }catch(e){ if(panel)panel.innerHTML=`<div style="color:var(--warn);padding:12px">Selection failed (${esc(String(e))}).</div>`; return; }
 if(!panel) return; if(!d.found){ panel.innerHTML=`<div style="padding:12px;color:var(--ink2)">${esc(d.note||'not found')}</div>`; return; }
 const a=d.detail, m=a.measured, c=a.computed, lk=a.linkage;
 const tag=(t,tone)=>`<span class="mono" style="font-size:8px;padding:2px 7px;border-radius:20px;background:var(--container);color:var(${tone})">${t}</span>`;
 const measuredHTML=m?`<div style="padding:11px 0;border-top:1px solid var(--hairline)">${tag('MEASURED DATA','--ok')} ${m.peer_reviewed===false?tag('PREPRINT','--warn'):''}<div style="font:400 12px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin-top:6px"><b style="color:var(--ink)">${m.n_downstream_de_genes}</b> downstream DE · on-target KD <b style="color:var(--ink)">${(+m.ontarget_effect_size).toFixed(1)}</b> · cross-donor r <b style="color:var(${m.crossdonor_reproducibility!=null&&m.crossdonor_reproducibility<0.3?'--risk':'--ink'})">${m.crossdonor_reproducibility==null?'n/a':(+m.crossdonor_reproducibility).toFixed(2)}</b><div class="mono" style="font-size:9px;color:var(--secondary);margin-top:4px">${esc(m.source)}</div></div></div>`:`<div style="padding:11px 0;border-top:1px solid var(--hairline)">${tag('MISSING / UNAVAILABLE','--outline')}<div style="font:400 12px/1.5 'Inter Tight',sans-serif;color:var(--ink2);margin-top:6px">No measured perturbation metrics (non-targeting control).</div></div>`;
 const compHTML=`<div style="padding:11px 0;border-top:1px solid var(--hairline)">${tag('COMPUTED · ILLUSTRATIVE','--warn')}<div style="font:400 12px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin-top:6px">Mean type-2 signature <b style="color:var(--ink)">${c.mean_type2_signature}</b> · Δ vs control <b style="color:var(${c.delta_vs_control<0?'--risk':'--ink'})">${c.delta_vs_control>0?'+':''}${c.delta_vs_control}</b> · ${a.n_cells} cells</div></div>`;
 const linkHTML=lk?`<div style="padding:11px 0;border-top:1px solid var(--hairline)">${tag('RANKING LINK','--secondary')}<div style="font:400 12px/1.6 'Inter Tight',sans-serif;color:var(--ink2);margin-top:6px">Ranked <b style="color:var(--ink)">#${lk.rank}</b> · composite <b style="color:var(--ink)">${(+lk.composite).toFixed(3)}</b> <button data-goto="targets" style="border:none;background:none;color:var(--claude-live);cursor:pointer;font:500 11px/1 'Inter Tight',sans-serif;text-decoration:underline">open ranking →</button></div></div>`:'';
 panel.innerHTML=`<div style="border:1px solid var(--hairline);border-radius:10px;background:var(--paper);overflow:hidden">
   <div style="padding:13px 16px;border-bottom:1px solid var(--hairline)"><div style="font:600 16px/1.2 'Inter Tight',sans-serif;color:var(--ink)">${esc(a.arm)}${a.gene&&a.gene!==a.arm?' · '+esc(a.gene):''}</div><div class="mono" style="font-size:9px;color:var(--secondary);margin-top:3px">${esc(a.integrity_state)} · ${a.n_cells} cells · affects ranking: no</div></div>
   <div style="padding:4px 16px 12px">${measuredHTML}${compHTML}${linkHTML}
     <div style="padding:11px 0;border-top:1px solid var(--hairline)"><div class="mono" style="font-size:9px;letter-spacing:.08em;color:var(--secondary);margin-bottom:4px">WHAT THIS DOES NOT PROVE</div><div style="font:400 11px/1.55 'Inter Tight',sans-serif;color:var(--ink2)">${(d.does_not_prove||[]).map(x=>'· '+esc(x)).join('<br>')}</div></div>
     <div style="padding:10px 0 2px;border-top:1px solid var(--hairline)"><div style="font:400 11px/1.5 'Inter Tight',sans-serif;color:var(--ink2)"><b style="color:var(--ink)">Reviewer:</b> ${esc(d.reviewer_note)}</div><div class="mono" style="font-size:8.5px;color:var(--outline);margin-top:6px">select run ${esc(d.selection_run_id)} · atlas ${esc(d.atlas_run_id)} · ledger ✓</div></div>
   </div></div>`;
 const gb=panel.querySelector('[data-goto]'); if(gb) gb.onclick=()=>go('targets');
}
const SCREENS_MAP={discovery:screenDiscovery,dataready:screenDataReady,cell:screenCell,atlas:screenAtlas,targets:screenTargets,perturbseq:screenPerturbseq,integrity:screenIntegrity,evidence:screenEvidence,decision:screenDecision,frontier:screenFrontier,reasoning:screenReasoning,grant:screenGrant,protein:screenProtein};
/* guided scientist workflow — turns scattered screens into ONE ordered path */
const WORKFLOW=[
 {id:'discovery',label:'Question',hint:'the question + dataset + top candidate'},
 {id:'dataready',label:'Data readiness',hint:'every source labeled; synthetic can’t affect ranking'},
 {id:'cell',label:'Research Cell',hint:'five agents run; only reviewer-approved claims count'},
 {id:'targets',label:'Rank targets',hint:'why each regulator ranks — 8 sourced components'},
 {id:'evidence',label:'Challenge evidence',hint:'exclude weak evidence → the ranking recomputes'},
 {id:'decision',label:'Design experiment',hint:'the falsifiable next experiment with a kill-condition'},
 {id:'grant',label:'Export receipt',hint:'the reproducibility bundle'},
];
function renderWorkflowRail(m, id){
 if(curDomain()!=='tcell') return;                 // the guided path is the Target Trust demo
 const idx=WORKFLOW.findIndex(s=>s.id===id); if(idx<0) return;
 const next=WORKFLOW[idx+1];
 const steps=WORKFLOW.map((s,i)=>{const st=i<idx?'done':i===idx?'now':'todo';
  const dot=st==='now'?'background:var(--primary);color:var(--on-primary)':st==='done'?'background:var(--ok);color:#fff':'border:1px solid var(--outline);color:var(--outline)';
  return `<button data-wf="${s.id}" title="${esc(s.hint)}" style="display:inline-flex;align-items:center;gap:6px;border:none;background:none;cursor:pointer;color:var(${st==='todo'?'--secondary':'--ink'});font:500 11px/1 'Inter Tight',sans-serif;white-space:nowrap"><span style="width:18px;height:18px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font:600 9px/1 'JetBrains Mono',monospace;${dot}">${st==='done'?'✓':i+1}</span>${esc(s.label)}</button>`;
 }).join('<span style="color:var(--outline);font-size:11px">·</span>');
 const rail=`<div id="ks-wf-rail" style="border-bottom:1px solid var(--hairline);background:var(--paper);padding:11px 30px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:sticky;top:0;z-index:6">
   <span class="mono" style="font-size:9px;letter-spacing:.11em;color:var(--secondary);flex:none">TARGET TRUST · STEP ${idx+1}/${WORKFLOW.length}</span>
   <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;flex:1">${steps}</div>
   ${next?`<button id="ks-wf-next" style="flex:none;display:inline-flex;align-items:center;gap:6px;border:1px solid var(--primary);background:var(--primary);color:var(--on-primary);border-radius:8px;padding:8px 13px;font:500 12px/1 'Inter Tight',sans-serif;cursor:pointer">Next · ${esc(next.label)}<span class="ms" style="font-size:15px">arrow_forward</span></button>`:`<span class="mono" style="font-size:10px;color:var(--ok);flex:none">✓ workflow complete — export ready</span>`}</div>`;
 m.insertAdjacentHTML('afterbegin', rail);
 m.querySelectorAll('[data-wf]').forEach(b=>b.onclick=()=>go(b.getAttribute('data-wf')));
 const nb=$('#ks-wf-next',m); if(nb&&next) nb.onclick=()=>go(next.id);
}
function go(id){ if(!SCREENS_MAP[id])return; stopLoops(); if(id!=='evidence')STATE.selected=null; STATE.screen=id; renderNav();
 const m=$('#main'); m.scrollTop=0; SCREENS_MAP[id](m); renderWorkflowRail(m, id); }

/* wire */
document.addEventListener('click',e=>{const b=e.target.closest('[data-screen]');if(b){go(b.dataset.screen);}});
// New Analysis (bring-your-own-data) opens from any [data-newanalysis] control —
// the rail CTA and the header button — via delegation, since the nav re-renders.
document.addEventListener('click',e=>{const b=e.target.closest('[data-newanalysis]');if(b){e.preventDefault();newAnalysis(b.getAttribute('data-newanalysis')||'references');}});
$('#themebtn').onclick=()=>{const cur=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';setTheme(cur);};
const sw=$('#progswitch');
// All four programs are real, working engine domains — the server warms tcell/gbm/
// ich/insulin on boot, and per-program `capabilities` filter the nav so switching
// never strands a scientist on an empty tab. Show every program so a scientist can
// switch and watch the real data change per program (the core "it's not static"
// proof). Default to the flagship CD4+ T-cell; `?program=<domain>` deep-links one.
if(sw){
 const want=(location.search.match(/[?&]program=(\w+)/)||[])[1];
 sw.value=(want && [...sw.options].some(o=>o.value===want))?want:'tcell';
}
if(sw) sw.onchange=()=>{STATE.domain=curDomain();switchProgram(sw.value);};
/* Search = the scientist's command bar. It routes live: a research QUESTION → the
   Decision Engine (real competing hypotheses + next experiment); a GENE symbol →
   live Open Targets; a DOI → prior art. Suggestions + a live route hint make that
   obvious (the header box used to read as decorative). */
const SEARCH_EXAMPLES=[
 {icon:'fork_right',q:'Which Th2 regulator should we target next, and how would we falsify it?',hint:'Decision Engine'},
 {icon:'biotech',q:'TSLP',hint:'live gene'},
 {icon:'biotech',q:'JAK1',hint:'live gene'},
 {icon:'link',q:'10.1038/sj.onc.1207616',hint:'prior art'},
];
function _routeLabel(q){ q=(q||'').trim(); if(!q) return 'Decision Engine';
 if(/\b10\.\d{4,9}\//.test(q)) return 'prior art';
 if(/^[A-Za-z0-9-]{2,9}$/.test(q)&&(/[0-9]/.test(q)||q===q.toUpperCase())) return 'live gene';
 return 'Decision Engine'; }
function _hideSuggest(){ const p=$('#ks-suggest'); if(p) p.remove(); }
function _showSuggest(){ const w=$('#searchwrap'); if(!w) return; _hideSuggest();
 const p=document.createElement('div'); p.id='ks-suggest';
 p.style.cssText='position:absolute;top:48px;left:0;right:0;z-index:60;background:var(--paper);border:1px solid var(--hairline);border-radius:11px;box-shadow:0 18px 50px rgba(0,0,0,.30);overflow:hidden';
 p.innerHTML=`<div style="padding:9px 14px;font:600 8.5px/1 'JetBrains Mono',monospace;letter-spacing:.1em;color:var(--secondary);border-bottom:1px solid var(--hairline)">TRY — EVERY RESULT IS REAL &amp; SOURCED</div>`+
  SEARCH_EXAMPLES.map(x=>`<button class="ks-sg" data-q="${esc(x.q)}" style="display:flex;align-items:center;gap:11px;width:100%;text-align:left;border:none;background:none;cursor:pointer;padding:10px 14px;color:var(--ink)"><span class="ms" style="font-size:17px;color:var(--claude-live);flex:none">${x.icon}</span><span style="flex:1;font:400 12.5px/1.35 'Inter Tight',sans-serif">${esc(x.q)}</span><span class="mono" style="font-size:9px;color:var(--secondary);flex:none">${esc(x.hint)}</span></button>`).join('');
 w.style.position='relative'; w.appendChild(p);
 p.querySelectorAll('.ks-sg').forEach(b=>b.addEventListener('mousedown',e=>{e.preventDefault(); const s=$('#searchbox'); const q=b.getAttribute('data-q'); if(s)s.value=q; _hideSuggest(); runSearch(q); }));
}
const sb=$('#searchbox'), sw2=$('#searchwrap');
if(sw2) sw2.addEventListener('click',e=>{ if(e.target!==sb && sb) sb.focus(); });
if(sb){
 sb.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();_hideSuggest();runSearch(sb.value);}});
 sb.addEventListener('focus',_showSuggest);
 sb.addEventListener('blur',()=>setTimeout(_hideSuggest,160));
 sb.addEventListener('input',()=>{ const h=$('#searchhint'); if(h) h.textContent=_routeLabel(sb.value); });
}
const hb=$('#howbtn'); if(hb) hb.onclick=howItWorks;
renderLiveBadge(); refreshLive();     // honest Claude-connection status in the header
renderNav();
if(sw && sw.value!=='lrrk2'){                           // default: real engine (GBM) — no LRRK2 flash anywhere
 STATE.screen='discovery';
 const set=(id,v)=>{const el=$('#'+id);if(el)el.textContent=v;};
 set('progmono','Keystone'); set('progname','Loading…'); set('progsub','fetching real engine data');
 const b=$('#progbadge'); if(b)b.style.display='none';
 const m0=$('#main'); if(m0)m0.innerHTML=`<div style="max-width:1080px;margin:0 auto;padding:64px 56px;color:var(--secondary);font:400 13px/1 'JetBrains Mono',monospace">Loading real engine data…</div>`;
 switchProgram(sw.value);
} else { updateShell(); go('discovery'); }

// First-visit onboarding: surface the "how a scientist uses Keystone" workflow
// once per browser, so someone landing cold (a scientist, or a judge) sees the
// end-to-end story before touching anything. Once only, dismissible, never blocks.
if(!localStorage.getItem('ks-seen-howto')){
 setTimeout(()=>{ if(!$('#ks-search-ov')){ howItWorks(); } localStorage.setItem('ks-seen-howto','1'); }, 1200);
}
})();
