'use strict';
let importPreview=null,importRequest=0;
let connectionConfig=null;
function renderExtras(data){
  const graph=data.graph;
  $('graph-count').textContent=`${graph.nodes.length} 个节点 · ${graph.edges.length} 条引用`+(graph.total_nodes>60?' · 仅显示关联较多的 60 条':'');
  const target=$('relation-graph');target.replaceChildren();
  if(!graph.nodes.length){target.append(node('div','保存原文并在草稿中关联证据后，可以在这里看见它们的联系。','empty'));return;}
  const svgNS='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(svgNS,'svg');svg.setAttribute('viewBox','0 0 960 '+Math.max(320,Math.ceil(graph.nodes.length/4)*130+50));svg.setAttribute('aria-label','资料引用关联图');
  const nodes=graph.nodes.map((r,i)=>({...r,x:120+(i%4)*240,y:70+Math.floor(i/4)*130}));
  const map=new Map(nodes.map(r=>[r.id,r]));
  graph.edges.forEach(e=>{const a=map.get(e.source),b=map.get(e.target),line=document.createElementNS(svgNS,'path');line.setAttribute('d',`M ${a.x} ${a.y-18} Q ${(a.x+b.x)/2} ${Math.min(a.y,b.y)-70} ${b.x} ${b.y-18}`);line.setAttribute('fill','none');line.setAttribute('class','relation-line');svg.append(line);});
  nodes.forEach(r=>{const g=document.createElementNS(svgNS,'g');g.setAttribute('class','graph-node node-'+r.kind);g.setAttribute('tabindex','0');g.setAttribute('role','button');g.setAttribute('aria-label',r.title);g.setAttribute('transform',`translate(${r.x},${r.y})`);const circle=document.createElementNS(svgNS,'circle');circle.setAttribute('r','17');const label=document.createElementNS(svgNS,'text');label.setAttribute('y','37');label.setAttribute('text-anchor','middle');label.textContent=r.title.length>12?r.title.slice(0,12)+'…':r.title;const type=document.createElementNS(svgNS,'text');type.setAttribute('y','54');type.setAttribute('text-anchor','middle');type.setAttribute('class','graph-type');type.textContent=names[r.kind];g.append(circle,label,type);g.onclick=()=>openRecord(r.id);g.onkeydown=e=>{if(e.key==='Enter')openRecord(r.id);};svg.append(g);});
  target.append(svg);
}
async function readTextFile(file){if(file.size>8*1024*1024)throw new Error('文件超过 8 MB，请先拆分。');return new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());}
$('import-file').onchange=async()=>{
  const request=++importRequest,file=$('import-file').files[0];
  importPreview=null;$('import-actions').hidden=true;$('import-preview').replaceChildren();
  if(!file){$('import-status').textContent='';return;}
  $('import-status').textContent='正在本地解析…';
  try{
    if(file.size>8*1024*1024)throw new Error('文件超过 8 MB，请先拆分。');
    const binary=/\.(pdf|docx)$/i.test(file.name);
    const body=binary?{filename:file.name,data:await fileBase64(file)}:{filename:file.name,text:await readTextFile(file)};
    if(request!==importRequest)return;
    const result=await api('/api/import-preview',body);
    if(request!==importRequest)return;
    importPreview=result;
    $('import-status').textContent=`识别到 ${result.items.length} 条资料，${result.items.filter(i=>i.duplicate).length} 条已存在。尚未写入资料库。`;
    result.items.forEach(item=>{const box=node('details','','import-item'),summary=node('summary'),label=node('label'),check=node('input');check.type='checkbox';check.value=item.key;check.checked=!item.duplicate;check.disabled=item.duplicate;label.append(check,node('span',item.title+(item.duplicate?' · 已存在，将跳过':'')));summary.append(label);box.append(summary,node('pre',item.content));$('import-preview').append(box);});
    $('import-actions').hidden=false;
  }catch(e){if(request===importRequest){$('import-status').textContent='无法导入：'+e.message;notice('导入预览未完成，请检查文件格式；扫描件需先由 Agent 做文字识别。',true);}}
};
$('commit-import').onclick=async()=>{
  if(!importPreview)return;
  const keys=[...document.querySelectorAll('#import-preview input:checked')].map(i=>i.value);
  if(!keys.length){notice('请选择至少一条新资料。',true);return;}
  const button=$('commit-import'),previewId=importPreview.preview_id,sensitivity=$('import-sensitivity').value;
  button.disabled=true;$('import-file').disabled=true;
  try{
    const result=await api('/api/import-commit',{preview_id:previewId,keys,sensitivity});
    notice(`已导入 ${result.imported} 条，跳过重复 ${result.skipped} 条。`+(sensitivity==='restricted'?'资料默认为受限；勾选“显示受限资料”可查看。':''));
    if(importPreview?.preview_id===previewId){$('import-actions').hidden=true;importPreview=null;$('import-file').value='';}
    await load();
  }catch(e){notice('导入未完成：'+e.message,true);}finally{button.disabled=false;$('import-file').disabled=false;}
};
function requestOptions(body){return{method:'POST',headers:{'Content-Type':'application/json','X-Personal-OS':'dashboard'},body:JSON.stringify(body)};}
$('download-backup').onclick=async()=>{if(!confirm('备份包含全部受限资料、草稿与历史，且未加密。确认下载到你自己控制的位置？'))return;const button=$('download-backup');button.disabled=true;try{const response=await fetch('/api/backup',requestOptions({}));if(!response.ok)throw new Error((await response.json()).error);const blob=await response.blob();const url=URL.createObjectURL(blob),a=node('a');a.href=url;a.download='personal-os-backup-'+new Date().toISOString().slice(0,10)+'.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice('备份已生成并交给浏览器下载，请保管好这个明文文件。');}catch(e){notice('备份失败：'+e.message,true);}finally{button.disabled=false;}};
async function fileBase64(file){if(file.size>32*1024*1024)throw new Error('备份超过 32 MB。');return await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('无法读取文件'));reader.readAsDataURL(file);});}
$('restore-file').onchange=async()=>{const file=$('restore-file').files[0];if(!file)return;if(!confirm('恢复会在当前资料库旁创建新的资料库，不会覆盖当前内容。确认继续？'))return;$('restore-result').textContent='正在校验并恢复…';try{const result=await api('/api/restore-backup',{data:await fileBase64(file)});$('restore-result').textContent=`已恢复 ${result.files} 个文件到：${result.restored_vault}。当前资料库未改变。重新启动时选择这个文件夹即可查看；Agent 配置也需使用新路径。`;notice('备份恢复成功，当前资料库保持原内容。');}catch(e){$('restore-result').textContent='恢复失败：'+e.message;notice('备份未恢复，请核对文件来源与完整性。',true);}};
function showConfig(){const config=connectionConfig.mcpServers['personal-os'];$('config-content').textContent=$('config-format').value==='toml'?`[mcp_servers.personal-os]\ncommand = ${JSON.stringify(config.command)}\nargs = ${JSON.stringify(config.args)}`:JSON.stringify(connectionConfig,null,2);}
$('show-config').onclick=async()=>{try{connectionConfig=await api('/api/config');showConfig();$('connection-config').hidden=false;}catch(e){notice('配置生成失败：'+e.message,true);}};
$('config-format').onchange=()=>{if(connectionConfig)showConfig();};
$('copy-config').onclick=async()=>{try{await navigator.clipboard.writeText($('config-content').textContent);notice('已复制当前资料库的接入配置。');}catch{notice('浏览器未允许复制，请手动选中配置文本。',true);}};
if(state.data)renderExtras(state.data);
