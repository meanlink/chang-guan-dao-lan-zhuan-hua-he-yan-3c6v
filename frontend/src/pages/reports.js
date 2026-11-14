import {jobs,reports} from '../api/entities.js';
import {download} from '../api/client.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {esc,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';

function scheduleArticle(r,isAdmin){
 const state=r.blocked
   ?'<span class="tag blocked">已拦截停发</span>'
   :(r.enabled?'<span class="tag live">运行中</span>':'<span class="tag">已暂停</span>');
 const action=r.blocked
   ?'<small class="blocked-note">撤回拦截 · 重新批准也不恢复，请另建计划</small>'
   :'<button class="button small" data-toggle="'+r.id+'" '+(isAdmin?'':'disabled')+'>'+(r.enabled?'暂停':'启用')+'</button>';
 return '<article '+(r.blocked?'class="is-blocked"':'')+'><div><strong>'+esc(r.name)+'</strong><p>'+esc(r.destination)+'</p>'
   +'<small>下次 '+date(r.next_run)+' · 周期 '+r.interval_seconds+' 秒</small>'
   +(r.blocked?'<p class="revoke-reason">'+esc(r.blocked_reason)+'</p>':'')+'</div><div class="schedule-side">'+state+action+'</div></article>';
}
function deliveryItem(d){
 const body='<div><strong>'+esc(d.filename||('拦截记录 #'+d.id))+'</strong><p>'+esc(d.destination)+' · '+date(d.created_at)+'</p>'
   +(d.blocked
     ?'<small class="blocked-note">已拦截 · 禁止下载，仅保留审计'+(d.blocked_reason?'：'+esc(d.blocked_reason):'')+'</small>'
     :'<small>SHA256 '+esc(d.checksum.slice(0,24))+'…</small>')+'</div>';
 const buttons=d.blocked
   ?'<div><span class="tag blocked">不可下载</span></div>'
   :'<div><button class="text-button" data-download="'+d.id+'" data-format="csv">CSV ↓</button><button class="text-button" data-download="'+d.id+'" data-format="json">JSON ↓</button></div>';
 return '<div class="delivery '+(d.blocked?'is-blocked':'')+'">'+body+buttons+'</div>';
}

export async function reportPage(){
 const [list,deliveries,allJobs]=await Promise.all([reports.list(),reports.deliveries(),jobs.list()]);
 workspace.reports=list;
 const approved=allJobs.filter(j=>j.approved&&j.status==='completed');
 const isAdmin=session.user.role==='admin';
 return heading('05 / DISTRIBUTION','定时分发与归档','把批准后的结果交付到本地业务收件箱。结论撤回后关联计划停发，旧归档留作审计但禁止下载。','<button class="button" id="refresh-reports">刷新收件箱 ↻</button>')
   +'<div class="report-grid"><section class="panel"><div class="section-title"><h2>创建分发计划</h2></div>'
   +'<form id="report-form"><label>简报名称<input name="name" required minlength="2" value="日间业务复核简报"></label>'
   +'<label>已批准分析<select name="job_id" required '+(approved.length?'':'disabled')+'>'+(approved.length?approved.map(j=>'<option value="'+j.id+'">'+esc(j.name)+'</option>').join(''):'<option value="">无有效批准结果（撤回后需重新批准并另建计划）</option>')+'</select></label>'
   +'<label>业务接收组<input name="destination" value="业务复核组 · 本地收件箱" required></label>'
   +'<div class="parameter-grid"><label>分发周期<select name="interval_seconds"><option value="86400">每日</option><option value="604800">每周</option><option value="60">每分钟（验收）</option></select></label>'
   +'<label>首次执行<select name="delay_seconds"><option value="0">立即</option><option value="60">1 分钟后</option><option value="3600">1 小时后</option></select></label></div>'
   +'<button type="submit" class="primary" '+(isAdmin&&approved.length?'':'disabled')+'>保存分发计划</button></form>'
   +'<p class="hint">由后台 worker 按到期时间生成文件。仅负责人可创建或暂停；被撤回拦截的计划不可恢复，只能另建。</p></section>'
   +'<section><div class="section-title"><h2>运行中的计划</h2><span>'+list.filter(r=>r.enabled&&!r.blocked).length+' 条已启用 · '+list.filter(r=>r.blocked).length+' 条已拦截</span></div>'
   +'<div class="schedule-list">'+list.map(r=>scheduleArticle(r,isAdmin)).join('')+'</div>'
   +'<section class="panel inbox"><div class="section-title"><h2>本地收件箱</h2><span>'+deliveries.length+' 份记录 · '+deliveries.filter(d=>d.blocked).length+' 份已拦截</span></div>'
   +deliveries.map(deliveryItem).join('')+(!deliveries.length?'<p class="empty">计划执行后，文件会出现在此处。等待片刻后刷新。</p>':'')+'</section></section></div>';
}
export function bindReports(refresh){
 document.querySelector('#refresh-reports').onclick=refresh;
 submit(document.querySelector('#report-form'),async f=>{
   await reports.create({name:f.get('name'),job_id:Number(f.get('job_id')),destination:f.get('destination'),interval_seconds:Number(f.get('interval_seconds')),delay_seconds:Number(f.get('delay_seconds'))});
   notify('计划已保存，后台将按到期时间归档');await refresh();
 });
 document.querySelectorAll('[data-toggle]').forEach(b=>b.onclick=async()=>{
   try{await reports.toggle(b.dataset.toggle);await refresh();}catch(e){notify(e.message,true);}
 });
 document.querySelectorAll('[data-download]').forEach(b=>b.onclick=()=>download(b.dataset.download,b.dataset.format).catch(e=>notify(e.message,true)));
}
