// @ts-check
/** @type {EventSource|null} */
let eventSource = null;
let labRunning = false;
/** @type {string|null} */
let currentLabId = null;
/** @type {(() => string|null)|null} */
let getModifiedCode = null;

/**
 * @param {string} labId
 * @param {boolean} serverMode
 * @param {{ getModifiedCode?: () => string|null }} [options]
 */
export function initTerminal(labId, serverMode, options) {
  currentLabId = labId;
  if (options?.getModifiedCode) getModifiedCode = options.getModifiedCode;
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

  // Check if we have modified code to run
  const modifiedCode = getModifiedCode ? getModifiedCode() : null;
  if (modifiedCode !== null) {
    // POST modified code to run-modified endpoint, then connect SSE
    fetch(`/api/run-modified/${currentLabId}`, {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: modifiedCode,
    }).then(response => {
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      function processChunk() {
        reader.read().then(({done, value}) => {
          if (done) { labRunning = false; return; }
          buffer += decoder.decode(value, {stream: true});
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              // Next line should be data
            } else if (line.startsWith("data: ")) {
              const eventData = JSON.parse(line.slice(6));
              // Determine event type from previous line context
              if (eventData.state) {
                if (eventData.state === "running") {
                  status.innerHTML = '<span class="terminal-spinner"></span> running (modified)';
                  status.className = "terminal-status running";
                  output.innerHTML = `<span class="cmd">$ ${(eventData.cmd || "").replace(/</g, "&lt;")} [modified]</span>\n`;
                } else if (eventData.state === "done") {
                  labRunning = false;
                  status.textContent = eventData.exit_code === 0 ? "done" : `exit ${eventData.exit_code}`;
                  status.className = eventData.exit_code === 0 ? "terminal-status" : "terminal-status error";
                  document.getElementById("stop-btn").style.display = "none";
                  document.getElementById("play-btn").style.display = "inline-flex";
                }
              } else if (eventData.text) {
                output.textContent += eventData.text;
                output.scrollTop = output.scrollHeight;
              }
            }
          }
          processChunk();
        }).catch(() => {
          labRunning = false;
          status.textContent = "connection lost";
          status.className = "terminal-status error";
          document.getElementById("stop-btn").style.display = "none";
          document.getElementById("play-btn").style.display = "inline-flex";
        });
      }
      processChunk();
    }).catch(err => {
      labRunning = false;
      output.textContent = `Error: ${err.message}`;
      status.textContent = "error";
      status.className = "terminal-status error";
      document.getElementById("stop-btn").style.display = "none";
      document.getElementById("play-btn").style.display = "inline-flex";
    });
  } else {
    // Original SSE-based run
    eventSource = new EventSource(`/api/run/${currentLabId}`);
    eventSource.addEventListener("status", e => {
      const d=JSON.parse(e.data);
      if(d.state==="running"){status.innerHTML='<span class="terminal-spinner"></span> running';status.className="terminal-status running";output.innerHTML=`<span class="cmd">$ ${d.cmd.replace(/</g,"&lt;")}</span>\n`;}
      else if(d.state==="done"){eventSource.close();eventSource=null;labRunning=false;status.textContent=d.exit_code===0?"done":`exit ${d.exit_code}`;status.className=d.exit_code===0?"terminal-status":"terminal-status error";document.getElementById("stop-btn").style.display="none";document.getElementById("play-btn").style.display="inline-flex";}
    });
    eventSource.addEventListener("output", e => { output.textContent+=JSON.parse(e.data).text; output.scrollTop=output.scrollHeight; });
    eventSource.onerror = () => { if(eventSource){eventSource.close();eventSource=null;} if(labRunning){labRunning=false;status.textContent="connection lost";status.className="terminal-status error";document.getElementById("stop-btn").style.display="none";document.getElementById("play-btn").style.display="inline-flex";} };
  }
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
