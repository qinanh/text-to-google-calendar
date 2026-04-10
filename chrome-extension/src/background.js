// Background service worker for Text to Google Calendar extension

const DEFAULT_SERVER = "http://localhost:8081";
const GOOGLE_CLIENT_ID = "887673305875-n57cauhsjj95j8rcq7h9tqilag7bntdf.apps.googleusercontent.com";
const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";
const GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo";
const SCOPES = "https://www.googleapis.com/auth/calendar";

// Create context menu on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "createCalendarEvent",
      title: "Create Calendar Event",
      contexts: ["selection"],
    });
    chrome.contextMenus.create({
      id: "previewCalendarEvent",
      title: "Preview Calendar Event",
      contexts: ["selection"],
    });
  });

  // Set default settings
  chrome.storage.sync.get(["serverUrl"], (data) => {
    if (!data.serverUrl) {
      chrome.storage.sync.set({ serverUrl: DEFAULT_SERVER, timezone: "America/Chicago" });
    }
  });
});

// ─── Settings & Auth helpers ───

async function getSettings() {
  const data = await chrome.storage.sync.get(["serverUrl", "apiKey"]);
  return {
    serverUrl: data.serverUrl || DEFAULT_SERVER,
    apiKey: data.apiKey || "",
  };
}

async function getGoogleToken() {
  const data = await chrome.storage.local.get(["googleToken", "googleRefreshToken", "googleTokenExpiry"]);
  // Check if token is still valid (with 60s buffer)
  if (data.googleToken && data.googleTokenExpiry && Date.now() < data.googleTokenExpiry - 60000) {
    return data.googleToken;
  }
  // Try refresh
  if (data.googleRefreshToken) {
    return await refreshGoogleToken(data.googleRefreshToken);
  }
  return null;
}

async function refreshGoogleToken(refreshToken) {
  try {
    const resp = await fetch(GOOGLE_TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: refreshToken,
        client_id: GOOGLE_CLIENT_ID,
      }),
    });
    const data = await resp.json();
    if (data.access_token) {
      await chrome.storage.local.set({
        googleToken: data.access_token,
        googleTokenExpiry: Date.now() + data.expires_in * 1000,
      });
      return data.access_token;
    }
  } catch (err) {
    console.error("Token refresh failed:", err);
  }
  return null;
}

// Google OAuth login via chrome.identity.launchWebAuthFlow
async function googleLogin() {
  const redirectUrl = chrome.identity.getRedirectURL();
  const authUrl = new URL(GOOGLE_AUTH_URL);
  authUrl.searchParams.set("client_id", GOOGLE_CLIENT_ID);
  authUrl.searchParams.set("redirect_uri", redirectUrl);
  authUrl.searchParams.set("response_type", "token");
  authUrl.searchParams.set("scope", SCOPES);
  authUrl.searchParams.set("prompt", "consent");

  const responseUrl = await chrome.identity.launchWebAuthFlow({
    url: authUrl.toString(),
    interactive: true,
  });

  const url = new URL(responseUrl);
  const params = new URLSearchParams(url.hash.substring(1));
  const accessToken = params.get("access_token");
  const expiresIn = parseInt(params.get("expires_in") || "3600");

  if (!accessToken) throw new Error("Failed to get access token");

  // Get user info for display
  const userResp = await fetch(GOOGLE_USERINFO_URL, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const userInfo = await userResp.json();

  await chrome.storage.local.set({
    googleToken: accessToken,
    googleTokenExpiry: Date.now() + expiresIn * 1000,
    googleUserEmail: userInfo.email || "",
    googleUserName: userInfo.name || "",
  });

  return { email: userInfo.email, name: userInfo.name };
}

async function googleLogout() {
  const data = await chrome.storage.local.get(["googleToken"]);
  if (data.googleToken) {
    try {
      await fetch(`https://oauth2.googleapis.com/revoke?token=${data.googleToken}`, {
        method: "POST",
      });
    } catch { /* ignore */ }
  }
  await chrome.storage.local.remove([
    "googleToken", "googleRefreshToken", "googleTokenExpiry",
    "googleUserEmail", "googleUserName",
  ]);
}

// ─── API request helper ───

async function apiRequest(endpoint, body) {
  const settings = await getSettings();
  const token = await getGoogleToken();
  if (!token) throw new Error("Not logged in. Please login with Google first.");

  const headers = { "Content-Type": "application/json" };
  headers["Authorization"] = `Bearer ${token}`;
  if (settings.apiKey) headers["X-API-Key"] = settings.apiKey;

  const resp = await fetch(`${settings.serverUrl}${endpoint}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Request failed");
  return data;
}

// ─── Notification helpers ───

function showNotification(title, message) {
  const id = "gcal-" + Date.now();
  try {
    chrome.notifications.create(id, {
      type: "basic",
      iconUrl: chrome.runtime.getURL("images/icon128.png"),
      title: title || "Text to Calendar",
      message: message || "",
    });
  } catch (err) {
    console.warn("Notification failed:", err);
  }
}

function sendToast(tabId, type, message, link) {
  if (!tabId) return;
  chrome.tabs.sendMessage(tabId, {
    action: "showToast", type, message, link,
  }).catch(() => {});
}

// ─── Context menu handler ───

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const selectedText = info.selectionText;
  if (!selectedText) return;
  const tabId = tab?.id;

  if (info.menuItemId === "createCalendarEvent") {
    try {
      const data = await apiRequest("/create_event", { text: selectedText });
      const count = data.count || 1;
      const summaries = (data.events || []).map(e => e.summary).join(", ");
      showNotification(`${count} Event(s) Created`, summaries || selectedText.slice(0, 80));
      sendToast(tabId, "success", `${count} event(s) created: ${summaries}`, data.eventLink);
    } catch (err) {
      showNotification("Error", err.message);
      sendToast(tabId, "error", `Failed: ${err.message}`);
    }
  } else if (info.menuItemId === "previewCalendarEvent") {
    try {
      const data = await apiRequest("/parse_event", { text: selectedText });
      const events = data.events || [data.event];
      const lines = events.map(e => {
        const start = e.start?.dateTime || e.start?.date || "N/A";
        return `${e.summary} | ${start}${e.location ? " | " + e.location : ""}`;
      });
      showNotification(`Preview (${events.length} event(s))`, lines.join("\n"));
    } catch (err) {
      showNotification("Error", err.message);
    }
  }
});

// ─── Message handler (from popup) ───

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "notify") {
    showNotification(request.title, request.message);
  } else if (request.action === "sendText") {
    handleCreateEvent(request.text, sender.tab);
  } else if (request.action === "googleLogin") {
    googleLogin().then(r => sendResponse({ success: true, ...r })).catch(e => sendResponse({ error: e.message }));
    return true;
  } else if (request.action === "googleLogout") {
    googleLogout().then(() => sendResponse({ success: true })).catch(e => sendResponse({ error: e.message }));
    return true;
  } else if (request.action === "getAuthStatus") {
    chrome.storage.local.get(["googleToken", "googleTokenExpiry", "googleUserEmail", "googleUserName"], (data) => {
      const loggedIn = !!(data.googleToken && data.googleTokenExpiry && Date.now() < data.googleTokenExpiry);
      sendResponse({ loggedIn, email: data.googleUserEmail, name: data.googleUserName });
    });
    return true;
  }
  return false;
});

async function handleCreateEvent(text, tab) {
  try {
    const data = await apiRequest("/create_event", { text });
    const summaries = (data.events || []).map(e => e.summary).join(", ");
    showNotification("Event Created", summaries || "Event created successfully");
    sendToast(tab?.id, "success", `Event(s) created: ${summaries}`, data.eventLink);
  } catch (err) {
    showNotification("Error", err.message);
  }
}
