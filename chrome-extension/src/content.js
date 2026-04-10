// Content script: shows floating toast notifications for event creation results

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "showToast") {
    showToast(request.type, request.message, request.link);
  }
});

// Floating toast notification
function showToast(type, message, link) {
  // Remove existing toast
  const existing = document.getElementById("gcal-toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.id = "gcal-toast";
  toast.className = `gcal-toast gcal-toast-${type}`;

  let html = `<span class="gcal-toast-msg">${escapeHtml(message)}</span>`;
  if (link) {
    html += ` <a href="${link}" target="_blank" class="gcal-toast-link">Open</a>`;
  }
  html += `<button class="gcal-toast-close">&times;</button>`;

  toast.innerHTML = html;
  document.body.appendChild(toast);

  // Close button
  toast.querySelector(".gcal-toast-close").addEventListener("click", () => {
    toast.classList.add("gcal-toast-hide");
    setTimeout(() => toast.remove(), 300);
  });

  // Auto-dismiss after 6 seconds
  setTimeout(() => {
    if (toast.parentNode) {
      toast.classList.add("gcal-toast-hide");
      setTimeout(() => toast.remove(), 300);
    }
  }, 6000);

  // Animate in
  requestAnimationFrame(() => {
    toast.classList.add("gcal-toast-show");
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
