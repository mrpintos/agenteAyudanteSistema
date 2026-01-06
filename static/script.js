async function fetchModels(){
  const sel = document.getElementById('modelSelect');
  sel.innerHTML = '<option>Cargando...</option>';
  try{
    const res = await fetch('/api/models');
    const data = await res.json();
    sel.innerHTML = '';
    (data.models || []).forEach(m => {
      const o = document.createElement('option'); o.value = m; o.textContent = m; sel.appendChild(o);
    });
  }catch(e){
    sel.innerHTML = '<option>Error al listar</option>';
  }
}

function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function mdStrongToHtml(text){
  // simple replacement of **bold** to <strong>
  return text.replace(/\*\*(.*?)\*\*/g, (_, m) => `<strong>${escapeHtml(m)}</strong>`);
}

function isPipeTable(text){
  if(!text) return false;
  const lines = text.split('\n').map(l=>l.trim());
  // find first line that starts with |
  const firstIdx = lines.findIndex(l => l.startsWith('|'));
  if(firstIdx === -1) return false;
  // require at least header and separator
  if(lines.length <= firstIdx + 1) return false;
  const sep = lines[firstIdx+1];
  // separator like |---|---|
  if(/^\|?\s*:?[-\s:|]+\s*\|?$/.test(sep)) return true;
  return false;
}

function renderPipeTable(text){
  const lines = text.split('\n');
  // find first pipe line
  let start = 0;
  while(start < lines.length && !lines[start].trim().startsWith('|')) start++;
  if(start >= lines.length) return null;
  // collect table lines starting at start until a non-pipe line
  const tableLines = [];
  for(let i=start;i<lines.length;i++){
    const l = lines[i];
    if(l.trim().startsWith('|')) tableLines.push(l.trim()); else break;
  }
  if(tableLines.length < 2) return null;

  // parse header and separator
  const headerLine = tableLines[0];
  const sepLine = tableLines[1];
  const headers = headerLine.split('|').slice(1,-1).map(h => h.trim());
  // build table element
  const table = document.createElement('table');
  table.className = 'pipe-table';
  const thead = document.createElement('thead');
  const trh = document.createElement('tr');
  headers.forEach(h => {
    const th = document.createElement('th');
    th.innerHTML = escapeHtml(h);
    trh.appendChild(th);
  });
  thead.appendChild(trh);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  for(let i=2;i<tableLines.length;i++){
    const cols = tableLines[i].split('|').slice(1,-1).map(c => c.trim());
    const tr = document.createElement('tr');
    cols.forEach(c => {
      const td = document.createElement('td');
      // convert **bold** inside cells
      const html = mdStrongToHtml(c);
      td.innerHTML = html;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  return table;
}

function renderTextWithTables(text){
  const lines = text.split('\n');
  const nodes = [];
  let buffer = [];
  const isSepLine = (l) => /^\|?\s*[:\-\s|]+\s*\|?$/.test(l.trim());

  for(let i=0;i<lines.length;){
    const line = lines[i];
    if(line.trim().startsWith('|') && i+1 < lines.length && isSepLine(lines[i+1])){
      // flush buffer
      if(buffer.length){
        const p = document.createElement('div');
        const txt = buffer.join('\n');
        p.innerHTML = mdStrongToHtml(escapeHtml(txt)).replace(/\n/g,'<br>');
        nodes.push(p);
        buffer = [];
      }

      // collect table lines
      const tableLines = [];
      tableLines.push(lines[i]);
      tableLines.push(lines[i+1]);
      i += 2;
      while(i < lines.length && lines[i].trim().startsWith('|')){
        tableLines.push(lines[i]);
        i++;
      }

      // build table
      const headerCols = tableLines[0].split('|').slice(1,-1).map(s=>s.trim());
      const table = document.createElement('table');
      table.className = 'pipe-table';
      const thead = document.createElement('thead');
      const trh = document.createElement('tr');
      headerCols.forEach(h=>{ const th = document.createElement('th'); th.innerHTML = escapeHtml(h); trh.appendChild(th); });
      thead.appendChild(trh); table.appendChild(thead);
      const tbody = document.createElement('tbody');
      for(let r=2;r<tableLines.length;r++){
        const cols = tableLines[r].split('|').slice(1,-1).map(s=>s.trim());
        const tr = document.createElement('tr');
        cols.forEach(c=>{ const td = document.createElement('td'); td.innerHTML = mdStrongToHtml(c); tr.appendChild(td); });
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
      nodes.push(table);
    } else {
      buffer.push(line);
      i++;
    }
  }
  if(buffer.length){
    const p = document.createElement('div');
    const txt = buffer.join('\n');
    p.innerHTML = mdStrongToHtml(escapeHtml(txt)).replace(/\n/g,'<br>');
    nodes.push(p);
  }
  return nodes;
}

// Render tool output with header, parameters (toggle), and output block
function renderToolOutput(text){
  const container = document.createElement('div');
  container.className = 'tool-container';

  // Try to extract header and parameters
  const headerMatch = text.match(/^==\s*(.+?)\s*==\n?/);
  let rest = text;
  let toolName = null;
  if(headerMatch){
    toolName = headerMatch[1];
    rest = text.slice(headerMatch[0].length);
  }

  const toolHeader = document.createElement('div');
  toolHeader.className = 'tool-header';
  toolHeader.textContent = toolName ? `Herramienta: ${toolName}` : 'Herramienta';
  container.appendChild(toolHeader);

  // buscar parámetros JSON al inicio
  let paramsText = null;
  const paramsMatch = rest.match(/^Parámetros:\s*(\{[\s\S]*?\})\n?/);
  if(paramsMatch){
    paramsText = paramsMatch[1];
    rest = rest.slice(paramsMatch[0].length);
  }

  if(paramsText){
    const paramsWrapper = document.createElement('div');
    paramsWrapper.className = 'params-wrapper';
    const paramsToggle = document.createElement('button');
    paramsToggle.className = 'params-toggle';
    paramsToggle.textContent = 'Mostrar parámetros';
    const paramsPre = document.createElement('pre');
    paramsPre.className = 'json-block';
    try{
      const obj = JSON.parse(paramsText);
      paramsPre.textContent = JSON.stringify(obj, null, 2);
    }catch(e){
      paramsPre.textContent = paramsText;
    }
    paramsPre.style.display = 'none';
    paramsToggle.onclick = () => {
      if(paramsPre.style.display === 'none'){
        paramsPre.style.display = 'block';
        paramsToggle.textContent = 'Ocultar parámetros';
      } else {
        paramsPre.style.display = 'none';
        paramsToggle.textContent = 'Mostrar parámetros';
      }
    };
    paramsWrapper.appendChild(paramsToggle);
    paramsWrapper.appendChild(paramsPre);
    container.appendChild(paramsWrapper);
  }

  const outPre = document.createElement('pre');
  outPre.className = 'code-block';
  outPre.textContent = rest.trim();
  container.appendChild(outPre);

  return container;
}

function isCodeLike(text){
  // kept for possible fallback but not used by default heuristics
  if(!text) return false;
  const lines = text.split('\n');
  if(lines.length > 1) return true;
  if(/\b(ps|top|ls|df|du|grep|awk|sed)\b/.test(text)) return true;
  if(/\|\s*-+\s*\|/.test(text)) return true;
  return false;
}

function appendMessage(role, text, displayAs){
  const log = document.getElementById('chatLog');
  const el = document.createElement('div');
  el.className = 'msg ' + role;
  const roleEl = document.createElement('div');
  roleEl.className = 'role';
  roleEl.textContent = role;
  const bodyEl = document.createElement('div');
  bodyEl.className = 'text';

  // Render as code only when server explicitly requests it or when role is 'tool'.
  const shouldRenderAsCode = displayAs === 'code' || role === 'tool';

  // Special-case: typing indicator for assistant when text is exactly '...'
  const isTypingIndicator = (role === 'assistant' && String(text).trim() === '...');

  // If text contains a pipe table, render text and tables preserving surrounding text
  if(isPipeTable(text)){
    const nodes = renderTextWithTables(text);
    if(nodes && nodes.length){
      nodes.forEach(n => bodyEl.appendChild(n));
    } else {
      bodyEl.innerHTML = escapeHtml(text).replace(/\n/g,'<br>');
    }
  } else if(shouldRenderAsCode){
    if(role === 'tool'){
      const toolNode = renderToolOutput(text);
      bodyEl.appendChild(toolNode);
    } else {
      const pre = document.createElement('pre');
      pre.className = 'code-block';
      pre.innerHTML = escapeHtml(text);
      bodyEl.appendChild(pre);
    }
  } else {
    if(isTypingIndicator){
      // build typing indicator element (three animated dots)
      const wrapper = document.createElement('div');
      wrapper.className = 'typing-indicator';
      for(let i=0;i<3;i++){
        const d = document.createElement('span');
        d.className = 'dot';
        wrapper.appendChild(d);
      }
      bodyEl.appendChild(wrapper);
    } else {
      bodyEl.innerHTML = escapeHtml(text).replace(/\n/g,'<br>');
    }
  }

  el.appendChild(roleEl);
  el.appendChild(bodyEl);
  log.appendChild(el);
  // Debug: indicar que se añadió un mensaje
  try{ console.log('appendMessage:', role, text); }catch(e){}
  // Defer scrolling para asegurar que el navegador ha renderizado el nuevo contenido
  ensureScrollToBottom(log);
}

function ensureScrollToBottom(log){
  try{
    requestAnimationFrame(()=>{
      requestAnimationFrame(()=>{
        const last = log.lastElementChild;
        if(last && last.scrollIntoView) {
          try{ last.scrollIntoView({behavior:'auto', block:'end'}); }catch(e){ }
        }
        // Ajustar el scroll del contenedor al máximo
        try{ log.scrollTop = Math.max(0, log.scrollHeight - log.clientHeight); }catch(e){ log.scrollTop = log.scrollHeight; }
        // También desplazar el scroll general de la ventana al final de la página
        try{ window.scrollTo({top: document.body.scrollHeight, behavior: 'auto'}); }catch(e){}
        // Fallback adicional por si el layout tarda un poco más
        setTimeout(()=>{
          const last2 = log.lastElementChild;
          if(last2 && last2.scrollIntoView){ try{ last2.scrollIntoView({behavior:'auto', block:'end'}); }catch(e){} }
          try{ last2 && (log.scrollTop = Math.max(0, log.scrollHeight - log.clientHeight)); }catch(e){ log.scrollTop = log.scrollHeight; }
          try{ window.scrollTo({top: document.body.scrollHeight, behavior: 'auto'}); }catch(e){}
        }, 80);
      });
    });
  }catch(e){ try{ log.scrollTop = log.scrollHeight; }catch(_){} }
}

document.addEventListener('DOMContentLoaded', ()=>{
  fetchModels();
  document.getElementById('sendBtn').onclick = async ()=>{
    const prompt = document.getElementById('prompt').value.trim();
    if(!prompt) return;
    appendMessage('user', prompt);
    document.getElementById('prompt').value = '';
    appendMessage('assistant','...');
    try{
      console.debug('fetch /api/chat', prompt);
      const res = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prompt})});
      const data = await res.json();
      console.debug('response /api/chat', data);
      // Re-renderizar todo el historial devuelto por el servidor (salta el system)
      const log = document.getElementById('chatLog');
      log.innerHTML = '';
      (data.messages || []).forEach(m => {
        if(m.role && m.role !== 'system') appendMessage(m.role, m.content || (m.text||''), m.display_as);
      });
      // asegurar scroll al final tras renderizado completo
      requestAnimationFrame(()=>{ const log = document.getElementById('chatLog'); const last = log.lastElementChild; if(last) last.scrollIntoView({behavior:'auto', block:'end'}); else log.scrollTop = log.scrollHeight; });
    }catch(e){
      console.error('fetch /api/chat error', e);
      appendMessage('assistant','Error al contactar con servidor');
    }
  };

  document.getElementById('changeModelBtn').onclick = async ()=>{
    const sel = document.getElementById('modelSelect');
    const model = sel.value;
    if(!model) return alert('Selecciona un modelo');
    try{
      const res = await fetch('/api/model',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({model})});
      const data = await res.json();
      alert('Modelo cambiado a: '+data.model);
    }catch(e){
      alert('Error al cambiar modelo');
    }
  };

  document.getElementById('clearBtn').onclick = ()=>{ document.getElementById('chatLog').innerHTML=''; };
});

