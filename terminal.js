let eventSource = null, labRunning = false, currentLabId = null;

export function initTerminal(labId, serverMode) {
  currentLabId = labId;
  document.getElementById("play-btn").onclick = runLab;
  document.getElementById("stop-btn").onclick = stopLab;
  document.getElementById("terminal-close").onclick = closeTerminal;
  document.getElementById("terminal-maximize").onclick = toggleSize;

  // Terminal resize handle
  const h = document.getElementById("terminal-resize-handle"), p = document.getElementById("terminal-panel");
  let startY, startH;
  h.addEventListener("mousedown", e => {
    e.preventDefault(); startY=e.clientY; startH=p.offsetHeight; h.classList.add("dragging");
    const drag = e => { p.style.height = Math.max(100,Math.min(window.innerHeight*.7,startH-(e.clientY-startY)))+"px"; };
    const up = () => { h.classList.remove("dragging"); document.removeEventListener("mousemove",drag); document.removeEventListener("mouseup",up); };
    document.addEventListener("mousemove",drag); document.addEventListener("mouseup",up);
  });
}

function runLab() {
  if (labRunning) return; labRunning = true;
  const panel=document.getElementById("terminal-panel"), output=document.getElementById("terminal-output"), status=document.getElementById("terminal-status");
  panel.classList.add("open"); output.textContent=""; status.textContent="";
  document.getElementById("play-btn").style.display="none";
  document.getElementById("stop-btn").style.display="inline-flex";
  eventSource = new EventSource(`/api/run/${currentLabId}`);
  eventSource.addEventListener("status", e => {
    const d=JSON.parse(e.data);
    if(d.state==="running"){status.innerHTML='<span class="terminal-spinner"></span> running';status.className="terminal-status running";output.innerHTML=`<span class="cmd">$ ${d.cmd.replace(/</g,"&lt;")}</span>\n`;}
    else if(d.state==="done"){eventSource.close();eventSource=null;labRunning=false;status.textContent=d.exit_code===0?"done":`exit ${d.exit_code}`;status.className=d.exit_code===0?"terminal-status":"terminal-status error";document.getElementById("stop-btn").style.display="none";document.getElementById("play-btn").style.display="inline-flex";}
  });
  eventSource.addEventListener("output", e => { output.textContent+=JSON.parse(e.data).text; output.scrollTop=output.scrollHeight; });
  eventSource.onerror = () => { if(eventSource){eventSource.close();eventSource=null;} if(labRunning){labRunning=false;status.textContent="connection lost";status.className="terminal-status error";document.getElementById("stop-btn").style.display="none";document.getElementById("play-btn").style.display="inline-flex";} };
}

function stopLab() { fetch(`/api/stop/${currentLabId}`); if(eventSource){eventSource.close();eventSource=null;} labRunning=false; closeTerminal(); }

function closeTerminal() {
  if(labRunning){fetch(`/api/stop/${currentLabId}`);if(eventSource){eventSource.close();eventSource=null;}labRunning=false;}
  const p=document.getElementById("terminal-panel"); p.classList.remove("open","fullscreen");
  document.getElementById("terminal-maximize").innerHTML="&#x26F6;";
  document.getElementById("stop-btn").style.display="none";
  document.getElementById("play-btn").style.display="inline-flex";
}

function toggleSize() {
  const p=document.getElementById("terminal-panel"); p.classList.toggle("fullscreen");
  document.getElementById("terminal-maximize").innerHTML=p.classList.contains("fullscreen")?"&#x29C9;":"&#x26F6;";
}
