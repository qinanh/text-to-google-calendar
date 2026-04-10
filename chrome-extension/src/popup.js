// Popup script for Text to Google Calendar extension

const DEFAULT_SERVER = "http://localhost:8081";

// Color ID -> name & hex mapping (Google Calendar)
const COLOR_MAP = {
  "1": {name: "Lavender", hex: "#7986cb"},
  "2": {name: "Sage", hex: "#33b679"},
  "3": {name: "Grape", hex: "#8e24aa"},
  "4": {name: "Flamingo", hex: "#e67c73"},
  "5": {name: "Banana", hex: "#f6bf26"},
  "6": {name: "Tangerine", hex: "#f4511e"},
  "7": {name: "Peacock", hex: "#039be5"},
  "8": {name: "Graphite", hex: "#616161"},
  "9": {name: "Blueberry", hex: "#3f51b5"},
  "10": {name: "Basil", hex: "#0b8043"},
  "11": {name: "Tomato", hex: "#d50000"},
  "14": {name: "Peacock", hex: "#039be5"},
};

// ─── Auth status ───

function updateAuthStatus() {
  chrome.runtime.sendMessage({ action: "getAuthStatus" }, (resp) => {
    const statusEl = document.getElementById("authStatus");
    const loginBtn = document.getElementById("btnLogin");
    const logoutBtn = document.getElementById("btnLogout");
    if (resp?.loggedIn) {
      statusEl.innerHTML = `Logged in as <strong>${escapeHtml(resp.email || "Unknown")}</strong>`;
      statusEl.className = "auth-status logged-in";
      loginBtn.style.display = "none";
      logoutBtn.style.display = "block";
    } else {
      statusEl.textContent = "Not logged in";
      statusEl.className = "auth-status logged-out";
      loginBtn.style.display = "block";
      logoutBtn.style.display = "none";
    }
  });
}
updateAuthStatus();

document.getElementById("btnLogin").addEventListener("click", () => {
  const btn = document.getElementById("btnLogin");
  btn.disabled = true;
  btn.textContent = "Logging in...";
  chrome.runtime.sendMessage({ action: "googleLogin" }, (resp) => {
    btn.disabled = false;
    btn.textContent = "Login with Google";
    if (resp?.error) {
      showStatus("error", resp.error);
    } else {
      updateAuthStatus();
    }
  });
});

document.getElementById("btnLogout").addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "googleLogout" }, () => {
    updateAuthStatus();
  });
});

// ─── Tab switching ───

document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");
  });
});

// ─── Settings load/save ───

chrome.storage.sync.get(["serverUrl", "timezone"], (data) => {
  document.getElementById("serverUrl").value = data.serverUrl || DEFAULT_SERVER;
  document.getElementById("timezone").value = data.timezone || "America/Chicago";
});

document.getElementById("btnSave").addEventListener("click", () => {
  const serverUrl = document.getElementById("serverUrl").value.trim();
  const timezone = document.getElementById("timezone").value.trim();
  chrome.storage.sync.set({ serverUrl, timezone }, () => {
    const saved = document.getElementById("settingsSaved");
    saved.style.display = "block";
    setTimeout(() => { saved.style.display = "none"; }, 2000);
  });
});

// ─── Helpers ───

async function getServerUrl() {
  return new Promise(resolve => {
    chrome.storage.sync.get(["serverUrl"], (data) => {
      resolve(data.serverUrl || DEFAULT_SERVER);
    });
  });
}

async function getAuthHeaders() {
  const local = await chrome.storage.local.get(["googleToken"]);
  const sync = await chrome.storage.sync.get(["apiKey"]);
  const headers = { "Content-Type": "application/json" };
  if (local.googleToken) headers["Authorization"] = `Bearer ${local.googleToken}`;
  if (sync.apiKey) headers["X-API-Key"] = sync.apiKey;
  return headers;
}

function showStatus(type, message) {
  const el = document.getElementById("status");
  el.className = `status ${type}`;
  el.innerHTML = message;
}

function clearStatus() {
  const el = document.getElementById("status");
  el.className = "status";
  el.innerHTML = "";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderEventPreview(events) {
  const preview = document.getElementById("eventPreview");
  if (!events || events.length === 0) {
    preview.classList.remove("show");
    return;
  }

  let html = events.length > 1
    ? `<div style="font-weight:600;margin-bottom:8px;color:#4285f4;">${events.length} events detected</div>`
    : "";

  events.forEach((event, idx) => {
    if (events.length > 1) {
      html += `<div style="font-weight:600;margin-top:${idx > 0 ? 10 : 0}px;padding-top:${idx > 0 ? 8 : 0}px;${idx > 0 ? "border-top:1px solid #e0e0e0;" : ""}">Event ${idx + 1}</div>`;
    }

    const colorId = event.colorId;
    const colorInfo = COLOR_MAP[colorId];
    const colorDot = colorInfo
      ? `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${colorInfo.hex};margin-right:4px;vertical-align:middle;"></span>`
      : "";

    if (event.summary) html += `<div class="field">${colorDot}<span class="field-label">Title:</span> <span class="field-value">${escapeHtml(event.summary)}</span></div>`;
    if (event.start) {
      const s = event.start.dateTime || event.start.date || "";
      html += `<div class="field"><span class="field-label">Start:</span> <span class="field-value">${escapeHtml(s)}</span></div>`;
    }
    if (event.end) {
      const e = event.end.dateTime || event.end.date || "";
      html += `<div class="field"><span class="field-label">End:</span> <span class="field-value">${escapeHtml(e)}</span></div>`;
    }
    if (event.location) html += `<div class="field"><span class="field-label">Location:</span> <span class="field-value">${escapeHtml(event.location)}</span></div>`;
    if (event.description) html += `<div class="field"><span class="field-label">Desc:</span> <span class="field-value">${escapeHtml(event.description)}</span></div>`;
    if (event.recurrence) html += `<div class="field"><span class="field-label">Recurrence:</span> <span class="field-value">${escapeHtml(event.recurrence.join(", "))}</span></div>`;
    if (event.attendees) html += `<div class="field"><span class="field-label">Attendees:</span> <span class="field-value">${escapeHtml(event.attendees.map(a => a.displayName ? `${a.displayName} <${a.email}>` : a.email).join(", "))}</span></div>`;
    if (event.conferenceData) html += `<div class="field"><span class="field-label">Conference:</span> <span class="field-value">Google Meet (auto-created)</span></div>`;
    if (colorInfo) html += `<div class="field"><span class="field-label">Color:</span> ${colorDot}<span class="field-value">${colorInfo.name}</span></div>`;
    if (event.visibility) html += `<div class="field"><span class="field-label">Visibility:</span> <span class="field-value">${escapeHtml(event.visibility)}</span></div>`;
    if (event.eventType && event.eventType !== "default") html += `<div class="field"><span class="field-label">Type:</span> <span class="field-value">${escapeHtml(event.eventType)}</span></div>`;
  });

  preview.innerHTML = html;
  preview.classList.add("show");
}

// ─── Preview event ───

document.getElementById("btnPreview").addEventListener("click", async () => {
  const text = document.getElementById("eventText").value.trim();
  if (!text) return showStatus("error", "Please enter event text.");

  const btn = document.getElementById("btnPreview");
  btn.disabled = true;
  showStatus("loading", '<span class="spinner"></span> Parsing events...');

  try {
    const serverUrl = await getServerUrl();
    const headers = await getAuthHeaders();
    const resp = await fetch(`${serverUrl}/parse_event`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Parse failed");

    renderEventPreview(data.events || [data.event]);
    clearStatus();
  } catch (err) {
    showStatus("error", `Error: ${escapeHtml(err.message)}`);
    document.getElementById("eventPreview").classList.remove("show");
  } finally {
    btn.disabled = false;
  }
});

// ─── Create event ───

document.getElementById("btnCreate").addEventListener("click", async () => {
  const text = document.getElementById("eventText").value.trim();
  if (!text) return showStatus("error", "Please enter event text.");

  const btn = document.getElementById("btnCreate");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Creating...';
  showStatus("loading", '<span class="spinner"></span> Creating calendar event(s)...');

  try {
    const serverUrl = await getServerUrl();
    const headers = await getAuthHeaders();
    const resp = await fetch(`${serverUrl}/create_event`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Creation failed");

    const count = data.count || 1;
    let msg = `${count} event(s) created! `;
    if (data.events) {
      msg += data.events.map(e => {
        let s = `"${escapeHtml(e.summary)}"`;
        if (e.eventLink) s += ` <a href="${e.eventLink}" target="_blank" class="event-link">Open</a>`;
        return s;
      }).join(" | ");
    }
    showStatus("success", msg);
    document.getElementById("eventPreview").classList.remove("show");

    chrome.runtime.sendMessage({
      action: "notify",
      title: `${count} Event(s) Created`,
      message: (data.events || []).map(e => e.summary).join(", "),
    });
  } catch (err) {
    showStatus("error", `Error: ${escapeHtml(err.message)}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Create Event";
  }
});
