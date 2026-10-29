const $=id=>document.getElementById(id);let timer;
async function api(path,opts){const r=await fetch(path,opts);const b=await r.json().catch(()=>({}));if(!r.ok)throw Error(b.detail||r.statusText);return b}
const pretty=x=>JSON.stringify(x,null,2);
async function refresh(){try{const d=await api('/api/tasks');$('tasks').innerHTML='';for(const t of d.tasks){const e=document.createElement('div');e.className='task';const a=document.createElement('div');a.textContent=t.mode.toUpperCase()+' · '+t.status;const s=document.createElement('small');s.textContent=t.id+' · '+t.prompt.slice(0,120);e.append(a,s);e.onclick=()=>show(t.id);$('tasks').append(e)}if(!d.tasks.length)$('tasks').textContent='No tasks yet.'}catch(e){$('tasks').textContent=e.message}}
async function show(id){try{const t=await api('/api/tasks/'+id);$('output').textContent=pretty(t);$('status').textContent=t.status+' · '+id;if(['queued','running'].includes(t.status)){clearTimeout(timer);timer=setTimeout(()=>show(id),1800)}await refresh()}catch(e){$('output').textContent=e.message}}
$('submit').onclick=async()=>{const prompt=$('prompt').value.trim();if(!prompt){$('status').textContent='Enter a task';return}$('submit').disabled=true;try{const t=await api('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:$('mode').value,prompt})});show(t.task_id)}catch(e){$('status').textContent=e.message}finally{$('submit').disabled=false}};
$('refresh').onclick=refresh;refresh();

async function loadKeyStatus(){try{const s=await api('/api/settings');$('keyStatus').textContent=s.api_key_configured?'Gateway key saved':'Gateway key required'}catch(e){$('keyStatus').textContent='Status unavailable'}}
$('saveKey').onclick=async()=>{const key=$('gatewayKey').value.trim();if(!key){$('keyStatus').textContent='Paste the unified key first';return}try{await api('/api/settings/gateway-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});$('gatewayKey').value='';$('keyStatus').textContent='Gateway key saved'}catch(e){$('keyStatus').textContent='Save failed: '+e.message}};
loadKeyStatus();
