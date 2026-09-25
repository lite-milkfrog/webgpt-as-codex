const LANG=document.documentElement.lang==="zh-CN"?"zh-CN":"en";
const S={
  en:{eyebrow:"Local control plane",subtitle:"Loopback-only control surface. Closing this page does not stop agent runtimes.",overview:"Overview",connectionUrls:"Connection URLs",runtimeActions:"Runtime actions",environment:"Environment",oauthPassword:"OAuth password",revealedPassword:"Revealed password",reveal:"Reveal",regenerate:"Regenerate",newPassword:"New password",setPassword:"Set password",oauthHint:"Changes are machine-local and require the owned Edge runtime to restart before they take effect.",components:"MCP inventory & migration",componentId:"Component ID",displayName:"Display name",role:"Role",endpoint:"Endpoint",addCandidate:"Add migration candidate",candidateHint:"Adding a candidate changes local registry visibility only. It does not grant routing or lifecycle authority.",activity:"Recent activity",copy:"Copy",open:"Open",productVersion:"Product version",deployment:"Deployment",gateway:"Gateway",oauth:"OAuth",https:"HTTPS / public edge",managerReady:"Manager ready",ready:"Ready",notReady:"Not ready",configured:"Configured",notConfigured:"Not configured",observed:"Observed",noLiveProof:"No live proof",publicMcp:"Public MCP",localGateway:"Local Gateway MCP",installTailscale:"Install / upgrade Tailscale",tailscaleReady:"Tailscale ready",migration:"Migration",version:"Version",remove:"Remove",custom:"custom",builtin:"built-in",noActivity:"No actions in this Manager process yet.",pending:"Working…",completed:"Completed",failed:"Failed",confirmAction:"Run this action?",confirmChange:"Apply this local configuration change?",restartPrompt:"Repository-managed component to restart",passwordSet:"OAuth password updated. Restart owned Edge to apply it.",passwordGenerated:"OAuth password regenerated. Restart owned Edge to apply it.",candidateAdded:"Migration candidate added without route/lifecycle authority.",candidateRemoved:"Migration candidate removed.",copied:"URL copied.",statusUnavailable:"Status unavailable"},
  "zh-CN":{eyebrow:"本机控制面",subtitle:"仅限本机回环访问。关闭此页面不会停止 Agent 或 MCP 运行时。",overview:"总览",connectionUrls:"连接地址",runtimeActions:"运行时操作",environment:"环境",oauthPassword:"OAuth 密码",revealedPassword:"已显示密码",reveal:"显示",regenerate:"重新生成",newPassword:"新密码",setPassword:"设置密码",oauthHint:"密码只保存在本机；修改后需要重启 WebGPT 自有 Edge 运行时才能生效。",components:"MCP 清单与迁移",componentId:"组件 ID",displayName:"显示名称",role:"角色",endpoint:"端点",addCandidate:"添加迁移候选",candidateHint:"添加候选只改变本机注册表可见性，不会自动获得路由权或生命周期控制权。",activity:"最近操作",copy:"复制",open:"打开",productVersion:"产品版本",deployment:"部署状态",gateway:"Gateway",oauth:"OAuth",https:"HTTPS / 公网边缘",managerReady:"Manager 就绪",ready:"就绪",notReady:"未就绪",configured:"已配置",notConfigured:"未配置",observed:"已观测",noLiveProof:"无实时证据",publicMcp:"公网 MCP",localGateway:"本机 Gateway MCP",installTailscale:"安装 / 升级 Tailscale",tailscaleReady:"Tailscale 就绪",migration:"迁移状态",version:"版本",remove:"移除",custom:"自定义",builtin:"内置",noActivity:"当前 Manager 进程还没有操作记录。",pending:"处理中…",completed:"已完成",failed:"失败",confirmAction:"确认执行此操作？",confirmChange:"确认应用这项本机配置变更？",restartPrompt:"要重启的仓库托管组件",passwordSet:"OAuth 密码已更新；重启 WebGPT 自有 Edge 后生效。",passwordGenerated:"OAuth 密码已重新生成；重启 WebGPT 自有 Edge 后生效。",candidateAdded:"迁移候选已添加，但没有获得路由权或生命周期控制权。",candidateRemoved:"迁移候选已移除。",copied:"地址已复制。",statusUnavailable:"状态暂不可用"}
};
const t=k=>S[LANG][k]||S.en[k]||k;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const state={config:null,status:null,actions:[],activity:[],pending:false,timer:null};
document.querySelectorAll("[data-i18n]").forEach(el=>{const key=el.dataset.i18n;if(S[LANG][key])el.textContent=S[LANG][key]});

async function api(url,opt={}){
  const options={...opt,headers:{...(opt.headers||{})}};
  if(options.method==="POST"){
    options.headers["Content-Type"]="application/json";
    options.headers["X-WebGPT-Control"]="1";
  }
  const response=await fetch(url,options);
  const body=await response.json().catch(()=>({error:String(response.status)}));
  if(!response.ok)throw Object.assign(new Error(body.error||body.status||String(response.status)),{payload:body});
  return body;
}
function notice(message,kind="info"){const el=document.querySelector("#notice");el.textContent=message||"";el.dataset.kind=kind}
function setPending(on,button){
  state.pending=on;
  document.querySelectorAll("[data-mutation]").forEach(el=>{el.disabled=on;el.setAttribute("aria-busy",String(on))});
  if(button)button.classList.toggle("is-pending",on);
  if(on)notice(t("pending"),"pending");
}
async function mutate(button,work,successText){
  if(state.pending)return;
  setPending(true,button);
  try{await work();notice(successText||t("completed"),"success");await refreshConfig();await refreshStatusOnce();await refreshActivity()}
  catch(error){notice(error.payload?.error||error.message||t("failed"),"error")}
  finally{setPending(false,button)}
}
function planeState(plane){
  const health=plane?.health||{};
  if(plane?.configured===false)return t("notConfigured");
  return Object.values(health).some(v=>v===true)?t("observed"):t("noLiveProof");
}
function card(label,value){return '<article class="card"><div class="label">'+esc(label)+'</div><div class="value">'+esc(value)+'</div></article>'}
function renderOverview(){
  if(!state.config||!state.status)return;
  const env=state.config.environment||{};
  const deployment=state.config.deployment||{};
  const pub=state.config.public_mcp_url?t("configured"):t("notConfigured");
  document.querySelector("#overview").innerHTML=[
    card(t("productVersion"),state.config.product_version||"unknown"),
    card(t("deployment"),deployment.edge_ready?t("ready"):deployment.gateway_ready?t("observed"):t("notReady")),
    card(t("gateway"),planeState(state.status.gateway)),
    card(t("oauth"),state.config.oauth_password?.configured?t("configured"):t("notConfigured")),
    card(t("https"),pub),
    card(t("managerReady"),env.ready_for_local_manager?t("ready"):t("notReady")),
    card(t("tailscaleReady"),env.tailscale?.ready?t("ready"):t("notReady"))
  ].join("");
}
function validUrl(raw){try{const u=new URL(raw);return ["http:","https:"].includes(u.protocol)?u.toString():null}catch{return null}}
function renderUrls(){
  if(!state.config)return;
  const rows=[[t("localGateway"),state.config.gateway_mcp_url],[t("publicMcp"),state.config.public_mcp_url]];
  document.querySelector("#urls").innerHTML=rows.map(([label,url])=>{
    const usable=Boolean(validUrl(url));
    return '<div class="url-row"><div class="url-value"><strong>'+esc(label)+'</strong><div>'+esc(url||t("notConfigured"))+'</div></div><div class="url-buttons"><button type="button" data-copy="'+esc(url||"")+'" '+(usable?"":"disabled")+'>'+esc(t("copy"))+'</button><button type="button" data-open="'+esc(url||"")+'" '+(usable?"":"disabled")+'>'+esc(t("open"))+'</button></div></div>';
  }).join("");
  document.querySelectorAll("[data-copy]").forEach(b=>b.onclick=()=>copyUrl(b.dataset.copy));
  document.querySelectorAll("[data-open]").forEach(b=>b.onclick=()=>openUrl(b.dataset.open));
}
async function copyUrl(raw){
  const url=validUrl(raw);if(!url)return;
  try{await navigator.clipboard.writeText(url)}
  catch{const area=document.createElement("textarea");area.value=url;area.setAttribute("readonly","");area.style.position="fixed";area.style.opacity="0";document.body.append(area);area.select();document.execCommand("copy");area.remove()}
  notice(t("copied"),"success");
}
function openUrl(raw){const url=validUrl(raw);if(!url)return;const opened=window.open(url,"_blank","noopener,noreferrer");if(opened)opened.opener=null}
function renderActions(){
  document.querySelector("#actions").innerHTML=state.actions.map(x=>'<button type="button" data-mutation data-action="'+esc(x.name)+'" data-confirm="'+String(x.confirmation_required)+'" '+(x.available?"":"disabled")+'>'+esc(x.label)+'</button>').join("");
  document.querySelectorAll("[data-action]").forEach(button=>button.onclick=()=>runAction(button));
}
async function runAction(button){
  const name=button.dataset.action;
  const confirmation=button.dataset.confirm==="true";
  if(confirmation&&!window.confirm(t("confirmAction")))return;
  const payload={confirm:confirmation};
  if(name==="restart"){
    const component=window.prompt(t("restartPrompt"),"mcpjungle");
    if(!component)return;
    payload.component=component.trim();
  }
  await mutate(button,()=>api("/api/actions/"+encodeURIComponent(name),{method:"POST",body:JSON.stringify(payload)}));
}
function renderEnvironment(){
  if(!state.config)return;
  const e=state.config.environment||{},ts=e.tailscale||{};
  document.querySelector("#environment").innerHTML=
    '<div class="component-meta"><span class="chip '+(e.ready_for_local_manager?"ok":"bad")+'">Manager: '+esc(e.ready_for_local_manager?t("ready"):t("notReady"))+'</span>'+
    '<span class="chip '+(e.ready_for_gateway?"ok":"bad")+'">Gateway: '+esc(e.ready_for_gateway?t("ready"):t("notReady"))+'</span>'+
    '<span class="chip '+(e.ready_for_edge?"ok":"bad")+'">Edge: '+esc(e.ready_for_edge?t("ready"):t("notReady"))+'</span>'+
    '<span class="chip '+(ts.ready?"ok":"bad")+'">Tailscale '+esc(ts.version||"unknown")+': '+esc(ts.ready?t("ready"):t("notReady"))+'</span></div>'+
    '<div class="actions"><button type="button" id="tailscale-install" data-mutation>'+esc(t("installTailscale"))+'</button></div>';
  document.querySelector("#tailscale-install").onclick=async event=>{
    if(!window.confirm(t("confirmChange")))return;
    await mutate(event.currentTarget,()=>api("/api/environment",{method:"POST",body:JSON.stringify({operation:"install-tailscale",confirm:true})}));
  };
}
function renderOAuth(){
  if(!state.config)return;
  document.querySelector("#oauth-status").textContent=state.config.oauth_password?.configured?t("configured"):t("notConfigured");
}
function renderComponents(){
  if(!state.config)return;
  document.querySelector("#components").innerHTML=(state.config.components||[]).map(c=>{
    const remove=c.custom&&!c.required?'<button type="button" class="danger" data-mutation data-remove="'+esc(c.id)+'">'+esc(t("remove"))+'</button>':"";
    const action=(c.lifecycle_state==="READY"||c.lifecycle_state==="READY_EXTERNAL")?(LANG==="zh-CN"?"无需处理":"No action needed"):(LANG==="zh-CN"?"检查本地启动器":"Check local launcher");
    return '<article class="component"><div class="component-head"><div><strong>'+esc(c.display_name)+'</strong><div class="muted">'+esc(c.id)+' · '+esc(c.role)+'</div></div><div>'+remove+'</div></div><div class="component-meta"><span class="chip">'+esc(c.lifecycle_state||"DOWN")+'</span><span class="chip">'+esc(c.ownership_mode||"external_local")+'</span><span class="chip">'+esc(c.auto_start?(LANG==="zh-CN"?"自动启动":"Auto start"):(LANG==="zh-CN"?"手动":"Manual"))+'</span><span class="chip">'+esc(c.custom?t("custom"):t("builtin"))+'</span><span class="chip">'+esc(t("version"))+': '+esc(c.version||"unknown")+'</span></div><div class="muted">'+esc(action)+'</div><div class="value">'+esc(c.endpoint||"")+'</div></article>';
  }).join("");
  document.querySelectorAll("[data-remove]").forEach(button=>button.onclick=async()=>{
    if(!window.confirm(t("confirmChange")))return;
    await mutate(button,()=>api("/api/components",{method:"POST",body:JSON.stringify({operation:"delete",id:button.dataset.remove,confirm:true})}),t("candidateRemoved"));
  });
}
function renderActivity(){
  const rows=state.activity||[];
  document.querySelector("#activity").innerHTML=rows.length?rows.map(row=>'<div class="activity-row"><time>'+esc(new Date(Number(row.at)*1000).toLocaleString(LANG))+'</time><div>'+esc(row.action)+(row.detail?' · '+esc(row.detail):'')+'</div><div class="activity-status">'+esc(row.status)+'</div></div>').join(""):'<div class="empty">'+esc(t("noActivity"))+'</div>';
}
async function refreshConfig(){state.config=await api("/api/local-config");renderOverview();renderUrls();renderEnvironment();renderOAuth();renderComponents()}
async function refreshActivity(){state.activity=(await api("/api/activity")).activity||[];renderActivity()}
async function refreshStatusOnce(){state.status=await api("/api/status");renderOverview()}
async function refreshStatusLoop(){
  try{await refreshStatusOnce();notice(document.querySelector("#notice").dataset.kind==="error"?"":document.querySelector("#notice").textContent)}
  catch(error){notice(t("statusUnavailable")+": "+error.message,"error")}
  const delay=Math.max(3000,Number(state.status?.poll_after_ms)||5000);state.timer=window.setTimeout(refreshStatusLoop,delay);
}
document.querySelector("#oauth-reveal").onclick=async event=>{
  if(!window.confirm(t("confirmChange")))return;
  await mutate(event.currentTarget,async()=>{const r=await api("/api/oauth-password",{method:"POST",body:JSON.stringify({action:"reveal",confirm:true})});document.querySelector("#oauth-revealed").value=r.password||""});
};
document.querySelector("#oauth-generate").onclick=async event=>{
  if(!window.confirm(t("confirmChange")))return;
  await mutate(event.currentTarget,async()=>{await api("/api/oauth-password",{method:"POST",body:JSON.stringify({action:"generate",confirm:true})});document.querySelector("#oauth-revealed").value=""},t("passwordGenerated"));
};
document.querySelector("#oauth-set-form").onsubmit=async event=>{
  event.preventDefault();if(!window.confirm(t("confirmChange")))return;
  const button=event.currentTarget.querySelector("button[type=submit]"),input=document.querySelector("#oauth-new"),value=input.value;
  await mutate(button,async()=>{await api("/api/oauth-password",{method:"POST",body:JSON.stringify({action:"set",value,confirm:true})});input.value="";document.querySelector("#oauth-revealed").value=""},t("passwordSet"));
};
document.querySelector("#component-form").onsubmit=async event=>{
  event.preventDefault();if(!window.confirm(t("confirmChange")))return;
  const form=event.currentTarget,data=new FormData(form),button=form.querySelector("button[type=submit]");
  const payload={operation:"create",confirm:true,id:String(data.get("id")||"").trim(),display_name:String(data.get("display_name")||"").trim(),role:String(data.get("role")||"").trim(),endpoint:String(data.get("endpoint")||"").trim()};
  await mutate(button,async()=>{await api("/api/components",{method:"POST",body:JSON.stringify(payload)});form.reset();form.elements.role.value="custom_mcp"},t("candidateAdded"));
};
(async()=>{try{const [cfg,actions,activity,status]=await Promise.all([api("/api/local-config"),api("/api/actions"),api("/api/activity"),api("/api/status")]);state.config=cfg;state.actions=actions.actions||[];state.activity=activity.activity||[];state.status=status;renderOverview();renderUrls();renderActions();renderEnvironment();renderOAuth();renderComponents();renderActivity();const delay=Math.max(3000,Number(status.poll_after_ms)||5000);state.timer=window.setTimeout(refreshStatusLoop,delay)}catch(error){notice(error.message||t("failed"),"error")}})();
