<script>
const A=window.location.origin,SN=new URLSearchParams(location.search).get('serial_number');
let D=null,CS=null,_pollTimer=null;
if(!SN)location.href='/records';

async function load(){
document.getElementById('ttl').textContent=SN;
try{const r=await fetch(A+'/api/audit-detail/'+encodeURIComponent(SN)+'?t='+Date.now());
if(!r.ok)throw 0;D=await r.json();
ren(D.record);rsl(D.ocr_files);rex(D.extracted_fields);rre(D.review_results);
rexSum(D.extracted_fields);
if(D.review_report){document.getElementById('pCard').style.display='';
document.getElementById('bRp').style.display='';
document.getElementById('pArea').textContent=D.review_report}
if(D.review_results.length>0)document.getElementById('rCard').style.display=''}
catch(e){document.getElementById('ttl').textContent='加载失败'}
checkExtractTask()}

function ren(r){
const f=[['流水号',r.serial_number],['场景',r.scenario_name],['提交人',r.submitter],
['日期',r.date||'-'],['地点',r.location||'-'],['对象',r.org||'-'],
['人数',r.guests],['人均',r.per_capita||0],['总额',r.total_amount||0],
['状态',r.status],['OCR',(r.ocr_file_count||0)+'/9']];
document.getElementById('rInfo').innerHTML=f.map(([k,v])=>
'<div><div class="ik">'+k+'</div><div class="iv">'+esc(v)+'</div></div>').join('')}

function rsl(oc){
document.getElementById('sg').innerHTML=oc.map((s,i)=>{
const c=s.status==='success'?'ok':s.status==='error'?'er':'';
const b=s.status==='success'?'<span class="bg ok">已识别</span>':
s.status==='error'?'<span class="bg er">失败</span>':'<span class="bg na">未上传</span>';
return'<div class="sl '+c+'" onclick="openS('+i+')"><div class="sn">'+s.label+'</div>'+
b+(s.original_filename?'<div class="sf">'+esc(s.original_filename)+'</div>':'')+'</div>'
}).join('')}

function rex(fs){
var skipFields=['_llm_text'];
if(!fs||!fs.length){
document.getElementById('exTableWrap').innerHTML=
'<p style="color:var(--c2);font-size:13px;padding:12px">暂无提取数据</p>';
document.getElementById('llmCards').innerHTML='';return}
var fieldSet={};
fs.forEach(function(f){
Object.keys(f.fields||{}).forEach(function(k){
if(skipFields.indexOf(k)===-1)fieldSet[k]=1})});
var fieldNames=Object.keys(fieldSet);
if(!fieldNames.length){
document.getElementById('exTableWrap').innerHTML=
'<p style="color:var(--c2);font-size:13px;padding:12px">暂无提取数据</p>';
document.getElementById('llmCards').innerHTML='';return}
var html='<thead><tr><th class="field-col">字段</th>';
fs.forEach(function(f){
html+='<th class="slot-col">'+f.slot_name+
'<span class="bg '+(f.status==='extracted'?'ok':'na')+
'" style="margin-left:4px;font-size:10px">'+f.status+'</span></th>'});
html+='</tr></thead><tbody>';
fieldNames.forEach(function(fn){
html+='<tr><td class="field-col">'+fn+'</td>';
fs.forEach(function(f){
var v=(f.fields||{})[fn];
html+='<td class="'+(v!=null&&v!==''?'has-value':'empty-val')+'">'+esc(v)+'</td>'});
html+='</tr>'});
html+='</tbody>';
document.getElementById('exTableWrap').innerHTML='<table class="ex-table">'+html+'</table>';
var cardsHtml='';
var hasLlm=false;
fs.forEach(function(f){
if(f.llm_text&&f.llm_text.trim()){
hasLlm=true;
var preview=esc(f.llm_text).substring(0,80);
var safeSlot=esc(f.slot_name).replace(/'/g,"\\'");
var safeText=f.llm_text.replace(/\\/g,"\\\\").replace(/'/g,"\\'");
cardsHtml+='<div class="llm-card" onclick="showLlmText(\''+safeSlot+'\',\''+safeText+'\')">';
cardsHtml+='<div class="llm-card-title">🤖 '+safeSlot+'</div>';
cardsHtml+='<div class="llm-card-preview">'+preview+'...</div></div>'});
document.getElementById('llmCards').innerHTML=hasLlm?cardsHtml:
'<p style="color:var(--c2);font-size:13px">暂无大模型原始回复</p>'}

function rre(rs){
if(!rs.length){document.getElementById('rCard').style.display='none';return}
document.getElementById('rList').innerHTML=rs.map(r=>
'<div class="ri"><span style="font-size:20px">'+(r.passed?'✅':'❌')+'</span>'+
'<div><div style="font-weight:600;font-size:13px">'+r.rule_name+
'<span class="sv sv-'+r.severity+'">'+r.severity+'</span></div>'+
'<div style="font-size:13px;color:var(--c2);margin-top:4px">'+esc(r.detail)+'</div></div></div>'
).join('')}

function openS(i){
const s=D.ocr_files[i];if(!s)return;CS=s;
document.getElementById('mT').textContent=s.label;
document.getElementById('mO').classList.add('show');
const v=document.getElementById('mV');v.innerHTML='';
if(s.ocr_record_id){const e=(s.original_file_path||'').split('.').pop().toLowerCase();
if(['jpg','jpeg','png','bmp','webp','gif'].includes(e))
v.innerHTML='<img src="'+A+'/api/ocr/record-file/'+s.ocr_record_id+'">';
else if(e==='pdf')
v.innerHTML='<iframe src="'+A+'/api/ocr/record-file/'+s.ocr_record_id+'"></iframe>';
fetch(A+'/api/ocr/records/'+s.ocr_record_id).then(r=>r.json()).then(
d=>document.getElementById('mM').textContent=d.markdown||'无')}
else{v.innerHTML='<p style="text-align:center;color:var(--c2);padding:24px">暂无</p>';
document.getElementById('mM').textContent=''}
const ef=D.extracted_fields.find(f=>f.slot_name===s.name);
if(ef&&ef.fields&&Object.keys(ef.fields).length){
document.getElementById('mF').innerHTML=Object.entries(ef.fields)
.filter(([k])=>k!=='_llm_text').map(
([k,v])=>'<div class="fr"><span class="fk">'+k+'</span><span class="fv">'+esc(v)+'</span></div>'
).join('')}
else document.getElementById('mF').innerHTML='<p style="color:var(--c2);font-size:12px">暂无</p>'}

function closeM(){document.getElementById('mO').classList.remove('show')}

async function doUp(e){
const f=e.target.files[0];if(!f||!CS)return;
const z=document.getElementById('uZ');z.innerHTML='<p>识别中...</p>';
const form=new FormData();form.append('file',f);form.append('slot_name',CS.name);
try{const r=await fetch(A+'/api/audit-detail/'+encodeURIComponent(SN)+'/ocr',{method:'POST',body:form});
const d=await r.json();
if(d.status==='success'||d.status==='duplicate'){toast(d.message||'上传成功');load();closeM()}
else toast('失败: '+d.message)}
catch(err){toast('错误: '+err.message)}
z.innerHTML='<p style="color:var(--c2);font-size:13px">点击上传新文件</p>'}

async function doEx(){
const b=document.getElementById('bEx');b.disabled=true;b.textContent='提取中...';
const methodEl=document.querySelector('input[name="exMethod"]:checked');
const method=methodEl?methodEl.value:'rule';
try{const r=await fetch(A+'/api/audit-detail/'+encodeURIComponent(SN)+'/extract?method='+
encodeURIComponent(method),{method:'POST'});const d=await r.json();
toast('提取完成: '+d.results.filter(r=>r.status==='success').length+'/'+d.results.length+
' (方式: '+(method==='llm'?'大模型':'规则')+')');load()}
catch(e){toast('错误: '+e.message)}b.disabled=false;b.textContent='字段提取'}

async function doRe(){
const b=document.getElementById('bRe');b.disabled=true;b.textContent='审核中...';
try{const r=await fetch(A+'/api/audit-detail/'+encodeURIComponent(SN)+'/review',{method:'POST'});
const d=await r.json();
if(d.status==='completed'){const p=d.results.filter(r=>r.passed).length;
toast('审核完成: '+p+'/'+d.results.length+'通过');load()}}
catch(e){toast('错误: '+e.message)}b.disabled=false;b.textContent='触发审核'}

function doRp(){if(!D||!D.review_report)return;
const b=new Blob([D.review_report],{type:'text/markdown'});const u=URL.createObjectURL(b);
const a=document.createElement('a');a.href=u;a.download=SN+'_审核报告.md';a.click();
URL.revokeObjectURL(u);toast('报告已下载')}

function toast(m){const t=document.getElementById('toast');t.textContent=m;
t.style.background=/成功|完成|通过/.test(m)?'var(--su)':'var(--er)';
t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000)}

function showLlmText(slot,text){
document.getElementById('llmModalTitle').textContent='🤖 '+slot+' - 大模型提取结果';
document.getElementById('llmModalBody').innerHTML=
'<div style="white-space:pre-wrap;line-height:1.8;font-size:14px;padding:8px">'+text+'</div>';
document.getElementById('llmModal').classList.add('show')}

function esc(s){if(s==null)return'-';const d=document.createElement('div');
d.textContent=String(s);return d.innerHTML}

function rexSum(fs){
const card=document.getElementById('exSumCard');
const el=document.getElementById('exSum');
if(!fs||!fs.length){card.style.display='none';return}
card.style.display='';
let done=0,total=0;
el.innerHTML=fs.map(f=>{
const c=f.status==='extracted'?'done':f.status==='extracting'?'running':'skip';
const fields=Object.entries(f.fields||{}).filter(
function(e){return e[0]!=='_llm_text'&&e[1]!=null&&e[1]!==''}).length;
if(f.status==='extracted')done++;total++;
return'<div class="ex-slot '+c+'"><div class="ex-slot-name">'+esc(f.slot_name)+'</div>'+
'<div class="ex-slot-status">'+(f.status==='extracted'?'✅ 已提取':
f.status==='extracting'?'⏳ 提取中':'⬜ 未提取')+'</div>'+
'<div class="ex-slot-fields">'+fields+' 个字段</div></div>'
}).join('');
document.getElementById('exSumStatus').textContent='共 '+total+' 个槽位，已提取 '+done+' 个'}

async function doExtractAsync(){
const b=document.getElementById('bEx');b.disabled=true;b.textContent='提交中...';
try{const r=await fetch(A+'/api/audit-detail/'+encodeURIComponent(SN)+'/extract-async',{method:'POST'});
const d=await r.json();
toast(d.message||'已提交后台提取');startPolling()}
catch(e){toast('错误: '+e.message)}
b.disabled=false;b.textContent='字段提取'}

function startPolling(){
if(_pollTimer)clearInterval(_pollTimer);
_pollTimer=setInterval(async()=>{
try{const r=await fetch(A+'/api/audit-detail/'+encodeURIComponent(SN)+'/extract-status');
const d=await r.json();
if(d.status==='completed'||d.status==='error'){
clearInterval(_pollTimer);_pollTimer=null;
toast(d.status==='completed'?'✅ 提取完成':'❌ 提取失败: '+(d.error||''));load()}
else if(d.status==='running'){
const card=document.getElementById('exSumCard');
if(card.style.display!=='none')
document.getElementById('exSumStatus').textContent='⏳ 后台提取中...'}
}catch(e){}},3000)}

function checkExtractTask(){
if(_pollTimer)return;
fetch(A+'/api/audit-detail/'+encodeURIComponent(SN)+'/extract-status')
.then(r=>r.json()).then(d=>{if(d.status==='running')startPolling()}).catch(()=>{})}

function openSettings(){
fetch(A+'/api/settings/llm').then(r=>r.json()).then(s=>{
document.getElementById('setTemp').value=s.llm_extract_temperature!=null?s.llm_extract_temperature:0.1;
document.getElementById('setMaxTokens').value=s.llm_extract_max_tokens!=null?s.llm_extract_max_tokens:4096;
document.getElementById('setAuto').checked=s.llm_extract_auto!==false;
document.getElementById('setO').classList.add('show')}).catch(()=>{})}

async function saveSettings(){
const data={llm_extract_temperature:parseFloat(document.getElementById('setTemp').value),
llm_extract_max_tokens:parseInt(document.getElementById('setMaxTokens').value),
llm_extract_auto:document.getElementById('setAuto').checked};
try{await fetch(A+'/api/settings/llm',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify(data)});
toast('设置已保存');document.getElementById('setO').classList.remove('show')}
catch(e){toast('保存失败: '+e.message)}}

document.addEventListener('DOMContentLoaded',load);
</script>