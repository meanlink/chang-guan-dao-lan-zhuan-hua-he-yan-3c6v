import {jobs,reports} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {chart} from '../components/common/chart.js';
import {table} from '../components/common/table.js';
import {status} from '../components/common/status.js';
import {ApprovalAction} from '../constants/enums.js';
import {esc,fmt,date,notify} from '../utils/dom.js';

function approvalBadge(j){
 if(j.approved)return '<span class="approval">已获业务批准</span>';
 if(j.revoked_at)return '<span class="approval revoked">批准已撤回</span>';
 return '<span class="approval pending">待负责人复核</span>';
}
function planState(r){
 if(r.blocked)return '<span class="tag blocked">已拦截停发</span>';
 return r.enabled?'<span class="tag live">运行中</span>':'<span class="tag">已暂停</span>';
}
function trailPanel(trail,linked){
 const rows=trail.length?trail.map(a=>'<li><strong>'+esc(ApprovalAction[a.action]||a.action)+'</strong>'
   +(a.action==='revoke'?'<p class="revoke-reason">撤回原因：'+esc(a.reason)+'</p>':'')
   +'<span>'+esc(a.actor)+' · '+date(a.at)+'</span></li>').join('')
   :'<li><span>暂无审批记录</span></li>';
 const plans=linked.length?linked.map(r=>'<li><strong>'+esc(r.name)+'</strong><span>'+esc(r.destination)+'</span>'+planState(r)
   +(r.blocked?'<p class="revoke-reason">'+esc(r.blocked_reason)+'</p>':'')+'</li>').join('')
   :'<li><span>该结论尚未关联分发计划</span></li>';
 return '<section class="panel two-columns"><div><div class="section-title"><h2>审批经过</h2><span>不可变审批记录</span></div><ul class="timeline approval-trail">'+rows+'</ul></div>'
   +'<div><div class="section-title"><h2>关联分发计划</h2><span>撤回后旧计划不恢复</span></div><ul class="timeline">'+plans+'</ul></div></section>';
}

export async function results(id){
 workspace.jobs=await jobs.list();
 const j=id?await jobs.get(id):(workspace.jobs.find(j=>j.id===workspace.selectedJob)||workspace.jobs[0]);
 if(j&&!workspace.jobs.some(x=>x.id===j.id))workspace.jobs.push(j);
 if(!j)return heading('04 / REVIEW','结果复核','尚无分析结果。')+'<div class="empty">先到分析工作台，选择批次并提交一次计算。<a href="#/workbench">前往工作台 ↗</a></div>';
 workspace.selectedJob=j.id;
 const [trail,allReports]=await Promise.all([jobs.approvals(j.id),reports.list()]);
 const linked=allReports.filter(r=>r.job_id===j.id);
 const r=j.result||{};
 const isAdmin=session.user.role==='admin';
 const revokeSheet=j.revoked_at
   ?'<div class="warning revoke-box"><strong>批准已撤回</strong><p>'+esc(j.revoked_reason)+'</p><small>'+esc(j.revoked_by)+' · '+date(j.revoked_at)+'</small>'
     +(isAdmin?'<button class="primary" id="reapprove-job">重新批准此结论（产生新审批记录）</button>':'')
     +'<p class="hint">重新批准不会恢复旧计划与旧归档，需在分发页另建计划。</p></div>'
   :'';
 const approveButtons=(j.status==='completed'&&isAdmin&&!j.approved&&!j.revoked_at)?'<button class="primary" id="approve-job">批准此业务结论</button>':'';
 const revokeButton=(j.status==='completed'&&isAdmin&&j.approved)?'<button class="danger" id="revoke-job">撤回批准（填写原因）</button>':'';
 return heading('04 / REVIEW','结果复核与业务解释',j.name,'<button class="button" id="refresh-results">刷新结果 ↻</button>')
   +'<div class="result-selector"><label>分析记录<select id="select-job">'+workspace.jobs.map(x=>'<option value="'+x.id+'" '+(x.id===j.id?'selected':'')+'>'+esc(x.name)+' · '+esc(x.status)+'</option>').join('')+'</select></label>'+status(j.status)+'<span>'+date(j.created_at)+'</span>'+approvalBadge(j)+'</div>'
   +(j.status==='completed'
     ?'<section class="result-lead"><p class="eyebrow">COMPUTED FINDING</p><h2>'+esc(r.summary)+'</h2><div class="metrics">'+(r.metrics||[]).map(m=>'<div><span>'+esc(m.label)+'</span><strong>'+esc(fmt(m.value))+'<small>'+esc(m.unit||'')+'</small></strong></div>').join('')+'</div></section>'
      +'<section class="panel">'+chart(r.chart)+'</section>'
      +'<div class="two-columns"><section class="panel"><div class="section-title"><h2>业务解释</h2><span>由计算结果生成</span></div><ol class="questions">'+(r.findings||[]).map(v=>'<li>'+esc(v)+'</li>').join('')+'</ol>'+(r.warnings||[]).map(v=>'<p class="warning">'+esc(v)+'</p>').join('')+'</section>'
      +'<section class="method-sheet compact"><p class="eyebrow">REPRODUCIBILITY</p><h3>计算口径与参数</h3><p>'+esc(r.method)+'</p><pre>'+esc(JSON.stringify(j.params,null,2))+'</pre>'+revokeSheet+approveButtons+revokeButton+'<p class="hint">仅批准结果可进入定时分发档案；撤回后关联计划停发、旧归档禁止下载。</p></section></div>'
      +trailPanel(trail,linked)
      +'<section class="panel"><div class="section-title"><h2>结果明细</h2><span>'+(r.table?.rows?.length||0)+' 行</span></div>'+table(r.table?.columns||[],r.table?.rows||[])+'</section>'
     :'<section class="panel empty">'+(j.status==='failed'?'计算失败：'+esc(j.error)+'。请返回工作台调整参数或数据。':'后台正在执行计算。点击刷新结果查看最新进展。')+'<a href="#/workbench">返回工作台 ↗</a></section>');
}
export function bindResults(refresh){
 document.querySelector('#refresh-results')?.addEventListener('click',refresh);
 document.querySelector('#select-job')?.addEventListener('change',e=>{workspace.selectedJob=Number(e.target.value);location.hash='#/results/'+e.target.value;});
 const approve=async el=>{try{await jobs.approve(workspace.selectedJob);notify('已批准，可创建分发计划');await refresh();}catch(e){notify(e.message,true);}};
 document.querySelector('#approve-job')?.addEventListener('click',approve);
 document.querySelector('#reapprove-job')?.addEventListener('click',approve);
 document.querySelector('#revoke-job')?.addEventListener('click',async()=>{
   const reason=window.prompt('请填写撤回批准的原因（将记入审批轨迹，并停用关联分发、禁止旧归档下载）');
   if(reason===null)return;
   if(!reason.trim()){notify('撤回原因不能为空',true);return;}
   try{await jobs.revoke(workspace.selectedJob,reason.trim());notify('已撤回批准：关联计划停发，旧归档仅留审计不可下载');await refresh();}
   catch(e){notify(e.message,true);}
 });
}
