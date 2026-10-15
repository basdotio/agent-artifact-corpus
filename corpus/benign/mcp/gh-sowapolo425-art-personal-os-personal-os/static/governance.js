'use strict';
const memoryStates={active:'当前有效',inactive:'已停用',expired:'已过期',not_yet_valid:'尚未生效',evidence_missing:'来源已删除',evidence_changed:'来源已更新，待复核',evidence_inactive:'来源已失效',unresolved_conflict:'矛盾待裁决',revoked:'已撤回',evidence_cycle:'来源循环，待复核'};
function field(parent,label,value='',type='text'){
  const wrapper=node('label',label),input=node(type==='textarea'?'textarea':'input');
  if(type!=='textarea')input.type=type;
  input.value=value;input.maxLength=5000;wrapper.append(input);parent.append(wrapper);return input;
}
function localDate(value){if(!value)return '';const d=new Date(value);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
function memoryForm(parent,memory={},decision=false){
  const controls={};
  controls.scope=field(parent,'适用范围（例如：今年预算、工作场景；不改变读取权限）',memory.scope||'');
  controls.valid_from=field(parent,'生效时间（可留空）',localDate(memory.valid_from),'datetime-local');
  controls.valid_until=field(parent,'失效时间（可留空）',localDate(memory.valid_until),'datetime-local');
  const label=node('label','使用状态'),select=node('select');
  for(const [v,t] of [['active','启用'],['inactive','停用']]){const o=node('option',t);o.value=v;select.append(o);}select.value=memory.state||'active';label.append(select);parent.append(label);controls.state=select;
  if(decision){
    for(const [key,title] of [['rationale','当时为什么这样决定'],['conditions','当时的条件与假设'],['expected_outcome','当时预期的结果'],['actual_outcome','后来实际发生的结果']]){
      controls[key]=field(parent,title,memory[key]||'','textarea');
      if(key!=='actual_outcome'&&memory[key])controls[key].disabled=true;
    }
    if(memory.reviewed_at)parent.append(node('p','上次复盘：'+format(memory.reviewed_at),'muted'));
  }
  return ()=>{const result={...memory};for(const [key,input] of Object.entries(controls)){if(input.value.trim())result[key]=key.startsWith('valid_')?new Date(input.value).toISOString():input.value;else delete result[key];}return result;};
}
function conflictControls(parent,p){
  if(p.record.claim_type!=='conflict')return null;
  const box=node('div','','panel');box.append(node('p','明确裁决后才进入有效记忆；保留“矛盾”类型与裁决记录。'));
  const select=node('select');for(const [v,t]of [['','请选择裁决'],['replace','用新结论替换旧记录'],['keep_both','保留两份，分别记录'],['scoped','按适用范围保留新结论']]){const o=node('option',t);o.value=v;select.append(o);}
  box.append(select);const scope=field(box,'选择按范围保留时，请填写新结论的适用范围');parent.append(box);
  return ()=>({resolution:select.value,scope:scope.value});
}
function renderGovernance(r){
  const host=$('record-governance');host.replaceChildren();
  host.append(node('h3','有效性与复盘'),node('p',memoryStates[r.effective_state]||'当前有效','chip pending'));
  const form=node('form'),read=memoryForm(form,r.memory||{},r.kind==='decision'),save=node('button','保存适用范围与复盘','button primary');save.type='submit';form.append(save);
  form.onsubmit=async e=>{e.preventDefault();save.disabled=true;try{await api('/api/memory',{id:r.id,revision:r.revision,memory:read(),restricted:restricted()==='1'});notice('已保存。关联结论如引用旧版本，将等待重新复核。');await openRecord(r.id);await load();}catch(e){notice(e.message,true);save.disabled=false;}};host.append(form);
  const preview=node('button','查看删除影响','button quiet');preview.type='button';host.append(preview);
  preview.onclick=async()=>{preview.disabled=true;const generation=recordRequest,scope=restricted();try{
    const plan=await api('/api/deletion-preview?'+new URLSearchParams({id:r.id,restricted:scope}));
    if(generation!==recordRequest||scope!==restricted())return;
    const box=node('div','','panel');box.append(node('p',`涉及 ${plan.affected_ids.length} 条记录、${plan.proposals} 份草稿，以及历史版本。`));
    plan.records.forEach(item=>box.append(node('p',item.title)));
    const mode=node('select');for(const [v,t]of [['source','仅移除原文：关联结论退出 Agent 检索，保留本地历史'],['deactivate','移除原文，同时明确停用关联结论'],['purge','永久清理：原文、派生记录、关联草稿与本地历史']]){const o=node('option',t);o.value=v;mode.append(o);}mode.value='source';box.append(mode,node('p',plan.warning,'muted'));
    const remove=node('button','按所选方式删除','button quiet');remove.type='button';box.append(remove);host.append(box);
    remove.onclick=async()=>{if(generation!==recordRequest||scope!==restricted())return;if(!confirm(mode.value==='purge'?'永久清理这些本地记录与历史，无法在本库恢复。确认？':'确认移除原文并使关联记忆失效？'))return;remove.disabled=true;try{const result=await api('/api/delete',{id:r.id,revision:plan.revision,impact:plan.impact,mode:mode.value,restricted:scope==='1'});clearLocalPreviews();closeRecord();notice(`本地处理完成，涉及 ${result.affected_ids.length} 条记录。外部上下文、导出文件和旧备份需另行清理。`);await load();}catch(e){notice(e.message,true);remove.disabled=false;}};
  }catch(e){notice(e.message,true);}finally{preview.disabled=false;}};
}
function clearLocalPreviews(){
  importRequest++;importPreview=null;$('import-actions').hidden=true;$('import-preview').replaceChildren();$('import-file').value='';
  if(typeof invalidateAnalysis==='function'){analysisSelected.clear();invalidateAnalysis();}
  if(typeof conversationRequest!=='undefined'){conversationRequest++;materialRequest++;$('conversation-list').replaceChildren();$('material-list').replaceChildren();}
}
const noteMemoryHost=node('div');$('note-form').insertBefore(noteMemoryHost,$('note-form').querySelector('[type=submit]'));
let readNoteMemory=memoryForm(noteMemoryHost,{},false);
const previousNoteKind=$('note-kind').onchange;
$('note-kind').onchange=()=>{previousNoteKind?.();noteMemoryHost.replaceChildren();readNoteMemory=memoryForm(noteMemoryHost,{},$('note-kind').value==='decision');};
function captureMemory(){return readNoteMemory();}
