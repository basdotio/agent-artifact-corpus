import { randomBytes } from 'node:crypto';
import { platformDefinitions } from '../platforms/registry.js';

/** Local controls never share the school's DOM or scripting world. */
export function authorizationHTML() {
  const nonce = randomBytes(18).toString('base64');
  const definitions = JSON.stringify(platformDefinitions.map(({ id, label }) => ({ id, label }))).replaceAll('<', String.fromCharCode(92) + 'u003c');
  return `<!doctype html><html lang="zh-Hans"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}'"><title>lms-cli</title><style>
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;background:#fff;color:#000;font:13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{padding:24px;max-width:500px;margin:auto}h1{font-size:18px;font-weight:600;margin:0;line-height:24px}p{margin:0}label{font-size:13px}select,button,input{font:inherit}select{width:100%;height:38px;margin:6px 0 16px;padding:0 10px;border:1px solid #000;background:#fff;color:#000}button{cursor:pointer;border:1px solid #000;background:#000;color:#fff;border-radius:5px;height:36px;padding:0 16px;font-weight:500}button:disabled{opacity:.5;cursor:default}:focus-visible{outline:2px solid #000;outline-offset:3px}.heading{display:flex;align-items:center;justify-content:space-between;gap:16px}.context{min-width:0}h1{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.experimental{font-size:11px;letter-spacing:.02em;margin-top:2px;opacity:.6}.origins{font-size:12px;opacity:.65;margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.options{display:flex;align-items:center;gap:20px;margin-top:18px}.options label{display:flex;align-items:center;gap:7px;white-space:nowrap}.options input{width:15px;height:15px;margin:0;accent-color:#000}.hint{font-size:12px;line-height:1.4;opacity:.65;margin-top:12px}.status{font-size:12px;line-height:18px;margin-top:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.selection{margin-top:24px}.actions{display:flex;align-items:center;justify-content:space-between;margin-top:20px}#cancel-login{background:#fff;color:#000;height:30px;padding:0 12px;font-size:12px;flex-shrink:0}body[data-busy] main{max-width:none;height:120px;padding:12px 20px;border-bottom:1px solid #000}body[data-busy] h1{font-size:14px;line-height:20px}body[data-busy] .options{margin-top:10px}body[data-busy] .status{margin-top:6px}body[data-busy] .hint,body[data-busy] .actions{display:none}@media(max-width:480px){main{padding:20px}.options{gap:16px}body[data-busy] main{padding:12px 14px}}
</style></head><body><main>
<div class="heading"><div class="context"><h1 id="heading">登录学校</h1><p class="experimental">实验性功能：自动填充与自动登录</p><p id="origins" class="origins"></p></div><button id="cancel-login" hidden title="取消本次登录（Esc）">取消</button></div>
<section id="selection" class="selection"><label for="school">学校 / 账号</label><select id="school"></select><label for="platform">登录平台</label><select id="platform"></select></section>
<div class="options"><label title="在本机加密保存密码，并保留学校允许的登录设备状态；取消勾选会清除"><input id="remember" type="checkbox" disabled>记住密码</label><label title="下次自动填充并登录；取消勾选即可停止自动操作"><input id="auto" type="checkbox" disabled>自动登录</label></div>
<p id="password-status" class="hint"></p><p id="status" class="status" role="status" aria-live="polite">正在准备登录…</p>
<div class="actions"><span class="hint">密码只保存在本机</span><button id="login" disabled>开始登录</button></div>
<p id="setup" class="hint" hidden>请运行 <code>lms setup</code> 添加学校。</p>
</main><script nonce="${nonce}">
const school=document.getElementById('school'),platform=document.getElementById('platform'),origins=document.getElementById('origins'),status=document.getElementById('status'),login=document.getElementById('login'),setup=document.getElementById('setup');
const remember=document.getElementById('remember'),auto=document.getElementById('auto'),passwordStatus=document.getElementById('password-status');
const cancel=document.getElementById('cancel-login'),heading=document.getElementById('heading'),selection=document.getElementById('selection');
const definitions=${definitions};
let latest={profiles:[],busy:false},saving=false,cancelling=false;
function option(value,label){const node=document.createElement('option');node.value=value;node.textContent=label;return node;}
function render(s){
  latest=s;
  const selected=s.lockedProfile||(s.profiles.some(p=>p.id===school.value)?school.value:s.active)||s.profiles[0]?.id||'';
  school.replaceChildren(...s.profiles.map(p=>option(p.id,p.label)));school.value=selected;
  const p=s.profiles.find(p=>p.id===school.value),available=p?definitions.filter(d=>p[d.id]).map(d=>d.id):[];
  const label=k=>definitions.find(d=>d.id===k)?.label||k;
  const previous=platform.value;
  platform.replaceChildren(...(available.length>1?[option('all','所有平台')]:[]),...available.map(k=>option(k,label(k))));
  platform.value=available.includes(previous)?previous:(available.length>1?'all':available[0]||'');
  const locked=s.currentPlatform||s.lockedPlatform;
  if(locked)platform.value=locked==='all'&&available.length===1?available[0]:locked;
  const chosen=platform.value==='all'?available:available.filter(k=>k===platform.value);
  origins.textContent=s.loginUrl||(p?chosen.map(k=>p[k]).join(' · '):'');origins.title=origins.textContent;
  heading.textContent=p?s.busy?p.label+' · '+chosen.map(label).join(' / '):p.label:'登录学校';
  const prefs=chosen.map(k=>s.preferences?.[p?.id]?.[k]||{});
  remember.checked=prefs.length>0&&prefs.every(o=>o.rememberPassword);
  auto.checked=prefs.length>0&&prefs.every(o=>o.autoLogin);
  remember.disabled=auto.disabled=saving||!chosen.length;
  const hasPassword=prefs.length>0&&prefs.every(o=>o.hasPassword);
  const hasTotp=prefs.length>0&&prefs.every(o=>o.totpConfigured);
  passwordStatus.textContent=remember.checked&&!hasPassword?'完成本次学校登录后保存密码':auto.checked&&hasTotp?'下次自动填充账号、密码和验证码并登录':auto.checked?'下次自动填充并登录':remember.checked?'下次自动填充，由你点击登录':'默认不保存账号密码';
  school.disabled=!!s.busy||saving||!!s.lockedProfile||!p;platform.disabled=!!s.busy||saving||!!s.lockedPlatform||!p;
  selection.hidden=!!s.busy||!!s.lockedProfile;
  login.disabled=!!s.busy||saving||!chosen.length;setup.hidden=!!p;
  cancel.hidden=!s.busy;cancel.disabled=!s.busy||cancelling;
  document.body.toggleAttribute('data-busy',!!s.busy);
  status.textContent=p?(s.message||'在学校页面完成登录'):'请先添加学校 / 账号';status.title=status.textContent;
}
 school.onchange=()=>{platform.value='';render({...latest,message:''});};
 platform.onchange=()=>render({...latest,message:''});
 async function saveOptions(){
  const options={rememberPassword:remember.checked,autoLogin:auto.checked};saving=true;render(latest);
  try{latest=await window.lms.setLoginOptions(school.value,platform.value,options);}
  catch{latest={...latest,message:'设置未保存，请重试；仍可手动登录。'};}
  finally{saving=false;render(latest);}
 }
 remember.onchange=()=>{if(!remember.checked)auto.checked=false;return saveOptions();};
 auto.onchange=()=>{if(auto.checked)remember.checked=true;return saveOptions();};
 cancel.onclick=async()=>{cancelling=true;render({...latest,message:'正在取消…'});try{latest=await window.lms.cancelLogin();}catch{latest={...latest,message:'请按 Esc 或关闭窗口取消。'};}finally{cancelling=false;render(latest);}};
 window.lms.onState(render);window.lms.state().then(render).catch(()=>{status.textContent='无法读取学校配置，请运行 lms setup 检查。';setup.hidden=false;});
 login.onclick=async()=>{try{render({...latest,busy:true,message:'正在打开学校页面…'});await window.lms.login(school.value,platform.value)}catch{render({...latest,busy:false,message:'无法开始登录，请重试。'})}};
</script></body></html>`;
}
