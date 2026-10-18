(function(){
'use strict';
var chapters=[].slice.call(document.querySelectorAll('.chapter'));
var root=document.querySelector('.ex')||document.body;
var navButtons=[].slice.call(document.querySelectorAll('.ex-rail button'));
var bar=document.querySelector('.ex .progress div');
var label=document.getElementById('ex-progress-label');
var views=[].slice.call(document.querySelectorAll('.ex-view button'));
var current=0;
function toChapterTop(){
  var layout=document.querySelector('.ex-layout');if(!layout)return window.scrollTo(0,0);
  var lift=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--bar-h'))||parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--gn-bar-h'))||0;
  var top=layout.getBoundingClientRect().top+window.pageYOffset-lift-16;
  if(window.pageYOffset>top)window.scrollTo(0,Math.max(0,top));
}
function show(i,push){
  current=Math.max(0,Math.min(chapters.length-1,i));
  chapters.forEach(function(c,n){c.classList.toggle('active',n===current);});
  navButtons.forEach(function(b,n){b.classList.toggle('active',n===current);});
  bar.style.width=((current+1)/chapters.length*100)+'%';
  if(label)label.textContent='Chapter '+(current+1)+' of '+chapters.length;
  document.getElementById('prev').disabled=current===0;
  document.getElementById('next').disabled=current===chapters.length-1;
  [].forEach.call(document.querySelectorAll('[data-goto]'),function(b){b.classList.toggle('active',parseInt(b.getAttribute('data-goto'),10)===current+1);});
  if(push!==false){try{history.replaceState(null,'','#'+chapters[current].id);}catch(e){}}
  if(push!==false){if(root.classList.contains('all')){if(chapters[current].scrollIntoView)chapters[current].scrollIntoView();}else{toChapterTop();}}
}
function fromHash(){var m=/^#ch-(\d+)/.exec(location.hash);show(m?parseInt(m[1],10)-1:0,false);}
navButtons.forEach(function(b,n){b.addEventListener('click',function(){show(n);});});
document.getElementById('prev').addEventListener('click',function(){show(current-1);});
document.getElementById('next').addEventListener('click',function(){show(current+1);});
document.addEventListener('keydown',function(e){
  if(e.target&&/INPUT|SELECT|TEXTAREA|BUTTON/.test(e.target.tagName))return;
  if(e.key==='ArrowRight')show(current+1); if(e.key==='ArrowLeft')show(current-1);});
function setView(v){
  root.classList.toggle('all',v==='all');
  views.forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-view')===v));});
  if(v==='all'){var c=chapters[current];if(c&&c.scrollIntoView)c.scrollIntoView();}
}
views.forEach(function(b){b.addEventListener('click',function(){setView(b.getAttribute('data-view'));});});
window.addEventListener('hashchange',fromHash);
fromHash();

/* quizzes */
[].forEach.call(document.querySelectorAll('.quiz'),function(q){
  var why=q.querySelector('.quiz-why');
  [].forEach.call(q.querySelectorAll('.quiz-opt'),function(b){
    b.addEventListener('click',function(){
      var right=b.getAttribute('data-right')==='1';
      [].forEach.call(q.querySelectorAll('.quiz-opt'),function(x){x.classList.remove('wrong');});
      b.classList.add(right?'right':'wrong');
      if(right){[].forEach.call(q.querySelectorAll('.quiz-opt'),function(x){if(x.getAttribute('data-right')==='1')x.classList.add('right');});}
      why.hidden=false;
      why.textContent=(right?'Right. ':'Not quite. ')+why.getAttribute('data-text');
    });
  });
  why.setAttribute('data-text',why.textContent);
});

/* assumption chain */
[].forEach.call(document.querySelectorAll('[data-widget="assumption-chain"]'),function(w){
  var note=w.querySelector('[data-note]');var cards=w.querySelectorAll('.card.a');var outlook=w.querySelector('.card.outlook');
  w.addEventListener('click',function(e){
    var act=e.target.getAttribute&&e.target.getAttribute('data-act'); if(!act)return;
    if(act==='trip'){
      cards[1].classList.add('found');
      setTimeout(function(){cards[1].classList.add('broken');outlook.innerHTML='Outlook: Visayas supply margin for 21 September 2026 is <b>comfortable</b>? One assumption under it is now in doubt.';},600);
      note.textContent='The desk found the one assumption the notice touches. The other two are untouched. Now the analyst has to decide whether the outlook still holds.';
    } else {
      [].forEach.call(cards,function(c){c.classList.remove('found','broken');});
      outlook.innerHTML='Outlook: Visayas supply margin for 21 September 2026 is <b>comfortable</b>.';
      note.textContent='Nothing has happened yet.';
    }
  });
});

/* three grids */
[].forEach.call(document.querySelectorAll('[data-widget="three-grids"]'),function(w){
  var note=w.querySelector('[data-note]');var parts=w.querySelectorAll('[data-info]');
  function pick(el){[].forEach.call(parts,function(p){p.classList.remove('active');});el.classList.add('active');note.textContent=el.getAttribute('data-info');}
  [].forEach.call(parts,function(p){p.addEventListener('mouseenter',function(){pick(p);});p.addEventListener('click',function(){pick(p);});});
});

/* PEDC clock */
[].forEach.call(document.querySelectorAll('[data-widget="pedc-clock"]'),function(w){
  var r=w.querySelector('.clock'),t=w.querySelector('[data-time]'),s=w.querySelector('[data-state]'),ev=w.querySelectorAll('[data-events] li');
  function pad(n){return (n<10?'0':'')+n;}
  function update(){
    var m=parseInt(r.value,10);t.textContent=pad(Math.floor(m/60))+':'+pad(m%60);
    var state='Unit 2 on line. The assumption of 83.7 MW looks fine.',cls='ok';
    if(m>=814&&m<907){state='Unit 2 is off. The day-level assumption no longer matches what the grid sees.';cls='bad';}
    else if(m>=907&&m<1020){state='Unit 2 is back. Was the assumption wrong, or only for 93 minutes? The analyst decides.';cls='warn';}
    else if(m>=1020&&m<1200){state='Yellow alert. The reserve is low. The unit is back.';cls='warn';}
    else if(m>=1200){state='The alert ended at 20:00. Unit 2 on line.';cls='ok';}
    s.textContent=state;s.className='state '+cls;
    [].forEach.call(ev,function(li){var at=parseInt(li.getAttribute('data-at'),10);li.classList.toggle('past',m>=at);li.classList.toggle('now',m>=at&&m<at+15);});
  }
  r.addEventListener('input',update);update();
});

/* cutoff pair */
[].forEach.call(document.querySelectorAll('[data-widget="cutoff-pair"]'),function(w){
  var note=w.querySelector('[data-note]');var btns=w.querySelectorAll('[data-cut]');var p=w.querySelector('[data-known="t1"]');
  [].forEach.call(btns,function(b){b.addEventListener('click',function(){
    [].forEach.call(btns,function(x){x.classList.remove('active');});b.classList.add('active');
    var after=b.getAttribute('data-cut')==='t1';p.classList.toggle('known',after);
    note.textContent=after?'One second later, the notice is known. The desk reads it with the register. Gemini answered: challenges. The return notice stays outside: it was not known yet.':'Before the notice, the desk may read only the register. The answer should be: the assumption stands.';
  });});
});

/* question set */
[].forEach.call(document.querySelectorAll('[data-widget="question-set"]'),function(w){
  var note=w.querySelector('[data-note]');
  [].forEach.call(w.querySelectorAll('.questions li'),function(li){li.addEventListener('click',function(){note.textContent=li.getAttribute('data-plain');});});
  var btn=w.querySelector('[data-act="wordings"]'),box=w.querySelector('.wordings');
  btn.addEventListener('click',function(){box.hidden=!box.hidden;btn.textContent=box.hidden?'Show the four forms of Q2 on the trip run':'Hide the four forms';});
});

/* label rule */
[].forEach.call(document.querySelectorAll('[data-widget="label-rule"]'),function(w){
  var out=w.querySelector('[data-label]'),note=w.querySelector('[data-note]');
  function v(q){return w.querySelector('[data-q="'+q+'"]').value;}
  function run(){
    var label,why;
    if(v('stable')==='no'){label='not enough evidence';why='The four presentation forms disagreed, so the desk trusts none of the answers.';}
    else if(v('q7')==='no'){label='not enough evidence';why='The model said the passages do not suffice. Nothing else counts.';}
    else if(v('q2')==='other'){label='unrelated';why='The event has nothing to do with this assumption.';}
    else if(v('q2')==='commercial operation'&&v('q3')==='same'){label='supports';why='The unit starts commercial operation on the same day. The assumption holds.';}
    else if(v('q2')==='testing'){label='challenges';why='Testing is not commercial operation. The milestone does not match.';}
    else if(v('q2')==='forced outage'||v('q3')==='after'){label='challenges';why='A forced outage, or a later date, challenges an availability assumption.';}
    else if(v('q3')==='before'){label='mixed';why='An earlier observation, but the direction answer on the trip says challenges, so the rules give mixed.';}
    else {label='mixed';why='The time is not stated, and the direction answer names a direction, so the support is partial.';}
    out.textContent=label;out.className=label.replace(/ /g,'-').replace('not-enough-evidence','insufficient');
    note.textContent=why+' The judgment records the rule that fired.';
  }
  [].forEach.call(w.querySelectorAll('select'),function(s){s.addEventListener('change',run);});run();
});

/* practice decision */
[].forEach.call(document.querySelectorAll('[data-widget="practice-decision"]'),function(w){
  var form=w.querySelector('[data-form]'),hist=w.querySelector('[data-history]'),note=w.querySelector('[data-note]');
  var names={keep:'keep the assumption at 83.7 MW',change:'change the assumption',open:'open the assumption for review'};
  form.addEventListener('submit',function(e){
    e.preventDefault();
    var reason=w.querySelector('[data-reason]').value.trim();
    if(!reason){note.textContent='The desk refuses a decision without a reason. Write one sentence.';return;}
    var d=form.querySelector('input[name=d]:checked').value;
    var li=document.createElement('li');li.className='new';
    li.textContent='13:4'+(hist.children.length)+', you: '+names[d]+'. Reason: "'+reason+'". Judgment at that time: challenges.';
    [].forEach.call(hist.children,function(c){c.classList.remove('new');});hist.appendChild(li);
    note.textContent=(d==='keep'?'A kept assumption with a reason counts as success. ':'')+'Saved to the history of your own copy. The AI did not decide. You did.';
    w.querySelector('[data-reason]').value='';
  });
});


/* finding -> mechanism */
[].forEach.call(document.querySelectorAll('[data-widget="finding-mechanism"]'),function(w){
  var M=['Code composes the label from the modal top answers. The thresholds test the modal answer as 1.0 or 0.0, never a probability, so calibration does not enter the label.',
    'Each question comes in four presentation forms: another option order, bracketed numbers for the options of a choice question, and reversed passages. Above a flip rate of 0.25 the set is unstable, and the label becomes not enough evidence.',
    'Each yes/no question also comes in a negated form, and the desk turns the answer back. A polarity gap above 0.3 makes the set unstable.',
    'Question 7 asks whether the passages suffice to decide. A modal no makes the label not enough evidence, and so does an unknown identity. That label is an answer, not a failure.',
    'The compiled task holds only passages whose known-at time is at or before the cutoff. A passage with no known availability time stays out, and nobody fills one in.',
    'The compiled task holds only the permitted passages. Authority and routing stay in code. A sentence in the evidence that gives instructions is data, not an instruction.'];
  var out=w.querySelector('[data-mech]');
  w.addEventListener('click',function(e){var f=e.target.getAttribute&&e.target.getAttribute('data-f'); if(f==null)return; [].forEach.call(w.querySelectorAll('[data-f]'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=M[+f];});
});
/* layer stack */
[].forEach.call(document.querySelectorAll('[data-widget="layer-stack"]'),function(w){
  var L=['Owns: fixed source versions with fingerprints, exact passages, series references, and the time each one became known. Never grants: factual acceptance of a claim. A copy of a claim is not a second source.',
    'Owns: the access filter, the availability and cutoff filter, reviewed identity mappings, units and quantity kinds. Never grants: equality from a similar name. A fuzzy match cannot change a belief.',
    'Owns: the fixed selection and layout of one task: actor, case, belief version, cutoff, permitted passages and one fingerprint. Never grants: any authority to a model. Compiling selects. It does not judge.',
    'Owns: answers inside the compiled task only. The question set returns typed option answers. Never grants: a label composed from model confidence, or acceptance of anything.',
    'Owns: the composed label, the rule that fired, the stability record, and escalation when the label is not enough evidence or the judgment is unstable. Never grants: a change to a belief. It proposes.',
    'Owns: the analyst\'s decision with a required reason, written with the head change and the audit entry in one transaction. Never grants: execution of anything, or permission to run a forecast.',
    'Owns: the outlook history, the earlier and the new positions, the open issues, and the typed proposal for the forecasting process. Never grants: forecast skill or commercial value. Those need evaluation.'];
  var out=w.querySelector('[data-info]');
  w.addEventListener('click',function(e){var l=e.target.getAttribute&&e.target.getAttribute('data-l'); if(l==null)return; [].forEach.call(w.querySelectorAll('.layer'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=L[+l];});
});
/* record axes */
[].forEach.call(document.querySelectorAll('[data-widget="record-axes"]'),function(w){
  var out=w.querySelector('[data-read]');
  function v(k){return w.querySelector('[data-ax="'+k+'"]').value;}
  function run(){
    var kind=v('kind'),rev=v('review'),av=v('avail'),mode=v('mode'); var t=[];
    t.push('This record is '+(kind==='observation'?'an observation: something that happened':kind==='assumption'?'an assumption: a position the analyst holds':kind==='prediction'?'a prediction: a model output about the future':kind==='reported claim'?'a reported claim: what a source says':kind==='review decision'?'a review decision: the analyst\'s act':'a '+kind)+'.');
    t.push('Its review state is '+rev+'.'+(rev==='accepted'&&kind==='prediction'?' Accepting it does not make it an observation; it stays a prediction the desk relies on.':'' ));
    t.push(av==='verified by cutoff'?'It was known at the cutoff, so a strict judgment may read it.':av==='later than cutoff'?'It became known after the cutoff, so a strict judgment must not see it.':av==='unknown'?'Nobody can say when it became known, so it is excluded from strict context and shown only in a labelled exploratory section.':'Access is denied: it does not exist for this actor, and the count does not reveal it.');
    t.push('It was produced in mode '+mode+(mode==='stored run'?': the answers were produced once and saved; the view says so.':mode==='synthetic test data'?': made up for a test, labelled so, never shown as real.':mode==='retrospective replay'?': judged today against a historical cutoff; never shown as a decision made then.':'.'));
    out.textContent=t.join(' ');
  }
  [].forEach.call(w.querySelectorAll('select'),function(s){s.addEventListener('change',run);}); run();
});
/* cutoff slider, in seconds: a notice posted at 13:39:37 is admitted at 13:39:37, not at 13:39:00 */
[].forEach.call(document.querySelectorAll('[data-widget="cutoff-slider"]'),function(w){
  var r=w.querySelector('.clock'),t=w.querySelector('[data-time]'),c=w.querySelector('[data-count]'),note=w.querySelector('[data-note]'),ps=w.querySelectorAll('[data-list] .passage');
  function pad(n){return (n<10?'0':'')+n;}
  function update(){
    var sec=+r.value; t.textContent=pad(Math.floor(sec/3600))+':'+pad(Math.floor(sec/60)%60)+':'+pad(sec%60); var n=0,x=0,u=0;
    [].forEach.call(ps,function(p){var k=p.getAttribute('data-known'); if(k==='unknown'){p.className='passage later';u++;return;} var known=+k<=sec; p.className='passage'+(known?' known':''); if(known)n++; else x++;});
    c.textContent=n+' admitted · '+x+' later than the cutoff · '+u+' unknown';
    note.textContent=sec<49177?'Before 13:39:37 the desk can read only the register. The trip has happened, but the feed has not logged the notice yet.':sec<57356?'The trip notice is in. The return notice is not: at this cutoff nobody could read it, so the model does not either.':'All four notices are in. The real-time schedule stays out: it has no recorded availability time, and the desk never fills one in.';
  }
  r.addEventListener('input',update); update();
});
/* transaction race */
[].forEach.call(document.querySelectorAll('[data-widget="transaction-race"]'),function(w){
  var steps=w.querySelectorAll('.walk li'),next=w.querySelector('[data-act="next"]'),reset=w.querySelector('[data-act="reset"]'),race=w.querySelector('[data-race]'),note=w.querySelector('[data-note]'); var n=0;
  function draw(){
    [].forEach.call(steps,function(li,i){li.classList.toggle('on',i<n);li.classList.toggle('now',i===n-1);
      if(li.hasAttribute('data-ok')){li.innerHTML='<b>Outcome.</b> '+(i<n?(race.checked?li.getAttribute('data-race'):li.getAttribute('data-ok')):'…');}
    });
    if(n===4&&race.checked){steps[4].style.display='none';}else{steps[4].style.display='';}
    next.disabled=n>=steps.length||(n>=4&&race.checked);
    note.textContent=race.checked&&n>=4?'The server wrote nothing. The page reloads the heads and the analyst decides again on the current state.':'The information cutoff stays the notice\'s. Only the audit cutoff moves.';
  }
  next.addEventListener('click',function(){n=Math.min(steps.length,n+1);draw();}); reset.addEventListener('click',function(){n=0;draw();}); race.addEventListener('change',draw); draw();
});
/* rule table: the fourteen rows of compose() in src/judgment/bundle.py, in its order */
[].forEach.call(document.querySelectorAll('[data-widget="rule-table"]'),function(w){
  var out=w.querySelector('[data-label]'),fired=w.querySelector('[data-fired]'),rows=w.querySelectorAll('[data-rows] tr');
  function v(q){return w.querySelector('[data-q="'+q+'"]').value;}
  function run(){
    var r,label,avail=v('avail')==='yes';
    if(v('stable')==='no'){r=0;label='not enough evidence';}
    else if(v('q7')==='no'){r=1;label='not enough evidence';}
    else if(v('q1')==='cannot_tell'){r=2;label='not enough evidence';}
    else if(v('q1')==='other'){r=3;label='unrelated';}
    else if(v('q2')==='other'||v('q2')==='grid_alert'){r=4;label='unrelated';}
    else if(v('q5')==='yes'){r=5;label='the earlier source\'s label, or not enough evidence';}
    else if(avail&&(v('q2')==='commercial_operation'||v('q2')==='return_to_service')&&v('q3')==='same'&&v('q4')==='no'){r=6;label='supports';}
    else if(avail&&v('q2')==='testing'){r=7;label='challenges';}
    else if(avail&&(v('q2')==='planned_outage'||v('q2')==='forced_outage'||v('q2')==='derating'||v('q3')==='after')){r=8;label='challenges';}
    else if(v('q3')==='before'&&v('q6')==='yes'){ if(v('q8')!=='challenges'){r=9;label='supports';} else {r=10;label='mixed';} }
    else if(v('q4')==='yes'&&(v('q3')==='same'||v('q3')==='before')){r=11;label='mixed';}
    else if(v('q3')==='not_stated'){r=12;label=v('q8')!=='neither'?'mixed':'not enough evidence';}
    else {r=13;label='not enough evidence';}
    [].forEach.call(rows,function(tr,i){tr.classList.toggle('fired',i===r);});
    out.textContent=label; out.className=label.indexOf('supports')===0?'supports':label==='unrelated'?'unrelated':label==='mixed'?'mixed':label==='challenges'?'challenges':'insufficient';
    fired.textContent='row '+(r+1)+' fired';
  }
  [].forEach.call(w.querySelectorAll('select'),function(s){s.addEventListener('change',run);}); run();
});
/* receipt sim */
[].forEach.call(document.querySelectorAll('[data-widget="receipt-sim"]'),function(w){
  var sel=w.querySelectorAll('[data-w]');
  function run(){
    var ans=[].map.call(sel,function(s){return s.value;}); var counts={}; ans.forEach(function(a){counts[a]=(counts[a]||0)+1;});
    var modal=Object.keys(counts).sort(function(a,b){return counts[b]-counts[a];})[0]; var flips=ans.filter(function(a){return a!==modal;}).length/ans.length;
    w.querySelector('[data-modal]').textContent=modal; w.querySelector('[data-flip]').textContent=flips.toFixed(2);
    var v=w.querySelector('[data-verdict]'); v.textContent=flips>0.25?'unstable: label becomes "not enough evidence"':'stable'; v.style.color=flips>0.25?'var(--bad)':'var(--ok)';
  }
  [].forEach.call(sel,function(s){s.addEventListener('change',run);}); run();
});
/* claim checker */
[].forEach.call(document.querySelectorAll('[data-widget="claim-checker"]'),function(w){
  var A=['Not allowed. The three-hour classifier flagged only 7 of 71 alert days before the operator\'s own notice. The desk reads notices. It does not beat them.',
    'Allowed. It is a recorded run of 14 October 2026 with a receipt: four presentation forms, eight questions, rule 9, and 9,743 tokens in. The grade is demonstrated.',
    'Not allowed. A judgment score is never an event probability. The label says what the evidence does to one belief, and nothing about the grid.',
    'Not allowed. Both scored 22 of 28, and the test split favours the single question, 8 of 10 against 7 of 10. The paper calls it a tie.',
    'Not allowed. The ranking lists what was unusual at the time, as evidence and not proof. Supply ranked first at 0.777, and the card names no cause.',
    'Allowed. The desk judges a decision by what people knew, not by its outcome. The paper writes this into its invariants.'];
  var out=w.querySelector('[data-answer]');
  w.addEventListener('click',function(e){var c=e.target.getAttribute&&e.target.getAttribute('data-c'); if(c==null)return; [].forEach.call(w.querySelectorAll('[data-c]'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=A[+c];});
});
/* pipeline layers */
[].forEach.call(document.querySelectorAll('[data-widget="pipeline-layers"]'),function(w){
  var L=['BigQuery external tables read the company\'s files where they are: five-minute prices and schedules, HVDC schedules, regional summaries, operator messages. Nothing is copied into Git.',
    'SQL builds one row per five-minute interval and region (292,839 rows to 29 September 2026), the price view, 253 parsed advisories and the alert windows they announce.',
    'Reserve condition labels from March 2026; 17 model inputs per row; a three-hour embargo between inputs and labels so nothing from the future leaks into training.',
    'A boosted-tree model trained locally and TabFM inside BigQuery tie on reserve-onset AUC (Visayas 0.947 against 0.943; Mindanao 0.967 against 0.961); zero-shot TimesFM alone is not competitive. TabFM ran once, on one context sample, with uncalibrated probabilities: a dated result, not rerun.',
    'One row per interval and region with fixed words: price band, reserve condition, shortfall severity, trend, import dependence, alert now and ahead. Alerts are rebuilt as of each interval from the advisories issued by then.',
    'The grid data build turns the exported snapshot into the small JSON files the page reads, under one content stamp. The event view and the event-type vectors travel with it. The build refuses an output folder that Git tracks.'];
  var out=w.querySelector('[data-info]');
  w.addEventListener('click',function(e){var l=e.target.getAttribute&&e.target.getAttribute('data-l'); if(l==null)return; [].forEach.call(w.querySelectorAll('.layer'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=L[+l];});
});
/* vector sum */
[].forEach.call(document.querySelectorAll('[data-widget="vector-sum"]'),function(w){
  var g=w.querySelector('[data-plot]'),note=w.querySelector('[data-note]'); var h=[0,0],pts=[[160,100]],names=[]; var MAX=90;
  function draw(){
    var s='';
    for(var i=1;i<pts.length;i++){s+='<line x1="'+pts[i-1][0]+'" y1="'+pts[i-1][1]+'" x2="'+pts[i][0]+'" y2="'+pts[i][1]+'" stroke="#f0b429" stroke-width="2"/>';}
    pts.forEach(function(p,i){s+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="'+(i===pts.length-1?5:3)+'" fill="'+(i===pts.length-1?'#f0b429':'#8ab4f8')+'"/>';});
    g.innerHTML=s;
  }
  w.addEventListener('click',function(e){
    var v=e.target.getAttribute&&e.target.getAttribute('data-v'); var act=e.target.getAttribute&&e.target.getAttribute('data-act');
    if(act==='reset'){h=[0,0];pts=[[160,100]];names=[];draw();note.textContent='Cleared. Add events again.';return;}
    if(!v)return; var d=v.split(',').map(Number); h=[h[0]+d[0],h[1]+d[1]]; var n=Math.hypot(h[0],h[1]); if(n>MAX){h=[h[0]*MAX/n,h[1]*MAX/n];}
    pts.push([160+h[0],100-h[1]]); names.push(e.target.textContent); draw();
    note.textContent='State after '+names.length+' events: ('+h[0].toFixed(0)+', '+h[1].toFixed(0)+')'+(n>MAX?', clipped to the maximum length':'')+'. Without the clip the order would not matter. The clip after each step keeps long days bounded, and once it engages the order does matter.';
  });
  draw();
});
/* cache classes */
[].forEach.call(document.querySelectorAll('[data-widget="cache-classes"]'),function(w){
  var A=['The page: Cache-Control: no-cache. The browser keeps a copy but revalidates every time, so a new build is seen at once; the page carries the current stamp in a meta tag.',
    'A design file under the stamp: public, max-age=31536000, immutable. Cached for a year; a changed byte changes the stamp and the URL.',
    'A replay file under the stamp: immutable too, and Firebase Hosting serves it from the edge. The first screen never touches the server.',
    'The same file without a stamp: no-store. The unversioned name exists for harnesses and is never cached.',
    'A session or any private answer: no-store. Nothing personal is ever cached by a proxy.',
    'The warm-up: no-store, so every visit really reaches the server once after the first paint.'];
  var out=w.querySelector('[data-answer]');
  w.addEventListener('click',function(e){var u=e.target.getAttribute&&e.target.getAttribute('data-u'); if(u==null)return; [].forEach.call(w.querySelectorAll('[data-u]'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=A[+u];});
});

/* request walk and task life */
[].forEach.call(document.querySelectorAll('[data-widget="request-walk"],[data-widget="task-life"],[data-widget="cold-timeline"],[data-kind="walk"]'),function(w){
  var steps=w.querySelectorAll('.walk li'),next=w.querySelector('[data-act="next"]'),reset=w.querySelector('[data-act="reset"]'),total=w.querySelector('[data-total]'),asleep=w.querySelector('[data-asleep]');
  var n=0;
  function draw(){
    var sum=0;
    [].forEach.call(steps,function(li,i){
      li.classList.toggle('on',i<n);li.classList.toggle('now',i===n-1);
      var t=li.querySelector('.t');
      if(li.hasAttribute('data-t')){
        var val=(asleep&&asleep.checked)?li.getAttribute('data-ct'):li.getAttribute('data-t');
        if(!t){t=document.createElement('span');t.className='t';li.appendChild(t);}
        t.textContent=i<n?val:'';
        if(i<n&&val)sum+=parseFloat(val);
      }
    });
    if(total)total.textContent=sum.toFixed(1)+' s so far';
    next.disabled=n>=steps.length;
  }
  next.addEventListener('click',function(){n=Math.min(steps.length,n+1);draw();});
  reset.addEventListener('click',function(){n=0;draw();});
  if(asleep)asleep.addEventListener('change',draw);
  draw();
});

/* the systems map: a node, the status filter and the arrows in order (DOC-4) */
[].forEach.call(document.querySelectorAll('[data-widget="systems-map"]'),function(w){
  var detail=w.querySelector('[data-detail]'),note=w.querySelector('[data-arrow-note]'),home=note.textContent;
  var arrows=[].slice.call(w.querySelectorAll('.arrow')),step=0;
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  /* A record is a link on the single-file copy. On the site the target is empty, so the detail
     shows the record's name and its path in the repository instead of a dead link. */
  function ref(label,href,path){
    if(href)return '<a href="'+esc(href)+'">'+esc(label)+'</a>';
    return esc(label)+' <code class="ref-path">'+esc(path)+'</code>';
  }
  function nodeOf(target){var t=target;while(t&&t!==w){if(t.getAttribute&&t.getAttribute('data-node'))return t;t=t.parentNode;}return null;}
  function pick(el){
    [].forEach.call(w.querySelectorAll('.node'),function(b){b.classList.toggle('active',b.getAttribute('data-node')===el.getAttribute('data-node'));});
    detail.innerHTML='<p class="d-name">'+esc(el.getAttribute('data-name'))+' <i class="st st-'+esc(el.getAttribute('data-status'))+'">'+esc(el.getAttribute('data-status'))+'</i></p>'
      +'<p><b>What it is.</b> '+esc(el.getAttribute('data-what'))+'</p>'
      +'<p><b>Its role.</b> '+esc(el.getAttribute('data-role'))+'</p>'
      +'<p><b>Status.</b> '+esc(el.getAttribute('data-status-note'))+'</p>'
      +'<p><b>Its numbers.</b> '+esc(el.getAttribute('data-numbers'))+' <small>('+ref(el.getAttribute('data-numbers-source-label'),el.getAttribute('data-numbers-source-href'),el.getAttribute('data-numbers-source-ref'))+')</small></p>'
      +'<p><b>Its source record.</b> '+ref(el.getAttribute('data-source-label'),el.getAttribute('data-source-href'),el.getAttribute('data-source-ref'))+'</p>';
  }
  [].forEach.call(w.querySelectorAll('.node'),function(b){b.addEventListener('click',function(){pick(b);});});
  var filters=w.querySelectorAll('[data-filter]');
  [].forEach.call(filters,function(b){b.addEventListener('click',function(){
    var f=b.getAttribute('data-filter'),dimmed=0;
    [].forEach.call(filters,function(x){var on=x===b;x.classList.toggle('active',on);x.setAttribute('aria-pressed',on?'true':'false');});
    [].forEach.call(w.querySelectorAll('.node'),function(el){var hide=f!=='all'&&el.getAttribute('data-status')!==f;el.classList.toggle('dim',hide);if(hide)dimmed++;});
    note.textContent=f==='all'?home:dimmed+' nodes are not '+f+'. Nothing is hidden: the rest of the map stays in place.';
  });});
  function drawArrows(){
    [].forEach.call(arrows,function(a,i){a.classList.toggle('on',i<step-1);a.classList.toggle('now',i===step-1);});
    note.textContent=step===0?home:'Arrow '+step+' of '+arrows.length+'. '+arrows[step-1].getAttribute('title');
  }
  w.querySelector('[data-act="next-arrow"]').addEventListener('click',function(){step=step>=arrows.length?1:step+1;drawArrows();});
  w.querySelector('[data-act="reset-arrows"]').addEventListener('click',function(){step=0;drawArrows();});
  drawArrows();
});

/* the path: a line per chapter, a pointer into the chapter and a done mark in the reader's browser (DOC-4) */
[].forEach.call(document.querySelectorAll('[data-widget="path"]'),function(w){
  var note=w.querySelector('[data-path-note]'),KEY='nowcast-explainer-done',total=w.querySelectorAll('[data-done]').length;
  function read(){try{var v=JSON.parse(window.localStorage.getItem(KEY)||'[]');return Object.prototype.toString.call(v)==='[object Array]'?v:[];}catch(e){return [];}}
  function write(v){try{window.localStorage.setItem(KEY,JSON.stringify(v));}catch(e){}}
  var done=read();
  function draw(){
    var n=0;
    [].forEach.call(w.querySelectorAll('[data-done]'),function(b){var on=done.indexOf(b.getAttribute('data-done'))>=0;if(on)n++;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on?'true':'false');});
    note.textContent=n===0?'No chapter carries a done mark yet.':n+' of '+total+' chapters carry a done mark in this browser.';
  }
  [].forEach.call(w.querySelectorAll('[data-done]'),function(b){b.addEventListener('click',function(){
    var id=b.getAttribute('data-done'),i=done.indexOf(id);
    if(i>=0){done.splice(i,1);}else{done.push(id);}
    write(done);draw();
  });});
  [].forEach.call(w.querySelectorAll('[data-goto]'),function(b){b.addEventListener('click',function(){show(parseInt(b.getAttribute('data-goto'),10)-1);});});
  draw();
});

/* the two Gemini roles: the real PEDC example (DOC-4) */
[].forEach.call(document.querySelectorAll('[data-widget="ai-roles"]'),function(w){
  var b=w.querySelector('[data-act="example"]'),box=w.querySelector('[data-example]');
  b.addEventListener('click',function(){box.hidden=!box.hidden;b.textContent=box.hidden?'Show the real PEDC example':'Hide the real PEDC example';});
});

/* the belief, its source and its time span (DOC-5) */
[].forEach.call(document.querySelectorAll('[data-widget="belief-span"]'),function(w){
  var note=w.querySelector('[data-note]');
  var src=w.querySelector('[data-part="source"]'),span=w.querySelector('[data-part="span"]');
  var srcText='<b>The source.</b> A driver\'s report, this morning.',spanText='<b>The time span.</b> Today.';
  var rest='Nothing has changed yet. A belief holds while its source and its time span hold.';
  w.addEventListener('click',function(e){
    var act=e.target.getAttribute&&e.target.getAttribute('data-act'); if(!act)return;
    if(act==='source'){src.innerHTML='<b>The source.</b> A rumour from a passer-by.';src.classList.remove('known');note.textContent='The source is weaker now. The desk keeps the belief and asks for a better source before anyone acts on it.';}
    else if(act==='span'){span.innerHTML='<b>The time span.</b> The whole week.';span.classList.remove('known');note.textContent='The belief now claims the whole week, and nothing supports that yet. The desk opens the belief for a fresh review.';}
    else {src.innerHTML=srcText;span.innerHTML=spanText;src.classList.add('known');span.classList.add('known');note.textContent=rest;}
  });
});

/* the decision, its line and its cost (DOC-5) */
[].forEach.call(document.querySelectorAll('[data-widget="decision-line"]'),function(w){
  var r=w.querySelector('input[type=range]'),out=w.querySelector('[data-amount]'),v=w.querySelector('[data-verdict]');
  var LINE=1000000;
  function fmt(n){return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,',');}
  function run(){
    var n=parseInt(r.value,10),over=n>=LINE;
    out.textContent=fmt(n)+' PHP';
    v.textContent=over?'At or above the line. The change matters, so the cost goes to the decision.':'Below the line. The desk leaves the position where it is.';
    v.className='state '+(over?'warn':'ok');
  }
  r.addEventListener('input',run); run();
});

/* the loop, one stage lit at a time (DOC-5) */
[].forEach.call(document.querySelectorAll('[data-widget="loop-stages"]'),function(w){
  var stages=w.querySelectorAll('.stage'),info=w.querySelector('[data-info]');
  var T=['Knowledge. The desk records the evidence with its source and the time it became known. The record is the desk\'s own work.',
    'Judgment. The model answers fixed questions and proposes a reading. It never accepts, and its answers stay on the record.',
    'Work. The analyst decides, keeps a reason and accepts or refuses the change. One write keeps the act, and that act is the receipt.',
    'Learning. The settled month scores the forecast. The first real pair is November to December 2026, and nothing reads the score yet.'];
  var n=0;
  function draw(){[].forEach.call(stages,function(s,i){s.classList.toggle('on',i<n);s.classList.toggle('now',i===n-1);});info.textContent=n===0?'Press Next to start.':T[n-1];}
  w.querySelector('[data-act="next"]').addEventListener('click',function(){n=n>=stages.length?1:n+1;draw();});
  w.querySelector('[data-act="reset"]').addEventListener('click',function(){n=0;draw();});
  draw();
});

/* the miss and its cause: belief, late signal, method (DOC-5) */
[].forEach.call(document.querySelectorAll('[data-widget="miss-cause"]'),function(w){
  var out=w.querySelector('[data-info]');
  var C=['The belief was wrong, so the belief changes and the position that rested on it comes back for review. The action or the belief is corrected: the first loop.',
    'The signal arrived after the cutoff, so the desk judged with what was known then, and the decision stands as it was made. What changes is when the desk looks.',
    'The method was wrong: the questions, the words or the line. The belief may still stand, and the rule table or the model goes back to the bench. The method or the goal changes: the second loop.'];
  w.addEventListener('click',function(e){var c=e.target.getAttribute&&e.target.getAttribute('data-c'); if(c==null)return; [].forEach.call(w.querySelectorAll('[data-c]'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=C[+c];});
});
/* the companion (third part): pick, switch, figure and the view validator */
function closest(el,sel,root){while(el&&el!==root){if(el.matches&&el.matches(sel))return el;el=el.parentNode;}return null;}
[].forEach.call(document.querySelectorAll('[data-kind="pick"]'),function(w){
  var out=w.querySelector('[data-out]');
  w.addEventListener('click',function(e){var b=closest(e.target,'[data-say]',w); if(!b)return;
    [].forEach.call(w.querySelectorAll('[data-say]'),function(x){x.classList.toggle('active',x===b);}); out.textContent=b.getAttribute('data-say');});
});
[].forEach.call(document.querySelectorAll('[data-kind="switch"]'),function(w){
  var state={};
  [].forEach.call(w.querySelectorAll('[data-set].active'),function(b){var p=b.getAttribute('data-set').split(':');state[p[0]]=p[1];});
  function draw(){
    [].forEach.call(w.querySelectorAll('[data-set]'),function(b){var p=b.getAttribute('data-set').split(':'),on=state[p[0]]===p[1];b.classList.toggle('active',on);b.setAttribute('aria-pressed',on?'true':'false');});
    [].forEach.call(w.querySelectorAll('[data-when]'),function(el){el.hidden=!el.getAttribute('data-when').split(' ').every(function(c){var p=c.split(':');return state[p[0]]===p[1];});});
  }
  w.addEventListener('click',function(e){var b=closest(e.target,'[data-set]',w); if(!b)return; var p=b.getAttribute('data-set').split(':'); state[p[0]]=p[1]; draw();});
  draw();
});
[].forEach.call(document.querySelectorAll('[data-kind="figure"]'),function(w){
  var d=w.querySelector('[data-detail]'),edges=[].slice.call(w.querySelectorAll('.fedges li'));
  function line(text){var p=document.createElement('p');p.textContent=text;d.appendChild(p);}
  w.addEventListener('click',function(e){var b=closest(e.target,'.fnode',w); if(!b)return;
    var id=b.getAttribute('data-id'),ins=[],outs=[];
    [].forEach.call(w.querySelectorAll('.fnode'),function(x){x.classList.remove('active');x.classList.remove('linked');});
    b.classList.add('active');
    edges.forEach(function(li){var a=li.getAttribute('data-a'),z=li.getAttribute('data-b');
      if(a===id||z===id){li.classList.add('on');var other=w.querySelector('.fnode[data-id="'+(a===id?z:a)+'"]'); if(other)other.classList.add('linked'); (a===id?outs:ins).push(li.textContent);} else li.classList.remove('on');});
    d.textContent=''; var h=document.createElement('p'),s=document.createElement('b'); s.textContent=b.textContent; h.appendChild(s);
    var g=closest(b,'.fgroup',w); if(g)h.appendChild(document.createTextNode(' · in '+g.querySelector('h4').textContent)); d.appendChild(h);
    line('Arrows in: '+(ins.length?ins.join(' · '):'none in this figure'));
    line('Arrows out: '+(outs.length?outs.join(' · '):'none in this figure'));
  });
});
[].forEach.call(document.querySelectorAll('[data-widget="view-validator"]'),function(w){
  var verdict=w.querySelector('[data-verdict]'),reasons=w.querySelector('[data-reasons]'),text=w.querySelector('[data-text]');
  var NAMES={cutoff:'the cutoff and the mode',families:'one block per family',unconfirmed:'the unconfirmed matches',withheld:'the withheld counts',ranking:'the ranking under its fixed heading'};
  function run(){
    var why=[];
    Object.keys(NAMES).forEach(function(k){if(!w.querySelector('[data-part="'+k+'"]').checked)why.push('Refused: the plan leaves out '+NAMES[k]+', a mandatory part of question kind Q1.');});
    if(w.querySelector('[data-part="chart"]').checked)why.push('Refused: a free chart is not in the catalogue. The model may only choose catalogue parts.');
    if(text.value==='numeral')why.push('Refused: the text holds the numeral 0.78, which quotes no record field by its id. The validator records the refusal.');
    verdict.textContent=why.length?'refused':'accepted'; verdict.className=why.length?'challenges':'supports';
    reasons.textContent=why.length?why.join(' '):(text.value==='quote'?'Every mandatory part is present, every part is in the catalogue, and the text quotes its one number by its field.':'Every mandatory part is present, every part is in the catalogue, and the text holds no numeral.');
  }
  [].forEach.call(w.querySelectorAll('input,select'),function(c){c.addEventListener('change',run);}); run();
});
})();
