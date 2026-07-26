const TQ_CATEGORY_COLORS = { info: "#3B82A6", success: "#2F9E6E", warning: "#D9A441", danger: "#D14343" };

document.addEventListener("DOMContentLoaded", () => {
  loadTqNotifications();
  setInterval(loadTqNotifications, 30000);

  const markAllBtn = document.getElementById("tqMarkAllRead");
  if (markAllBtn) {
    markAllBtn.addEventListener("click", (e) => {
      e.preventDefault();
      fetch("/api/notifications/read-all", { method: "POST" }).then(loadTqNotifications);
    });
  }
});

function loadTqNotifications() {
  const list = document.getElementById("tqNotifList");
  const badge = document.getElementById("tqNotifBadge");
  if (!list || !badge) return;

  fetch("/api/notifications")
    .then((r) => r.json())
    .then((data) => {
      badge.textContent = data.unread_count;
      badge.classList.toggle("d-none", data.unread_count === 0);

      if (!data.items.length) {
        list.innerHTML = '<div class="text-center text-muted py-3" style="font-size:0.8rem;">You&rsquo;re all caught up.</div>';
        return;
      }

      list.innerHTML = data.items.map(tqRenderNotifItem).join("");

      list.querySelectorAll("[data-notif-id]").forEach((node) => {
        node.addEventListener("click", () => {
          const id = node.getAttribute("data-notif-id");
          const link = node.getAttribute("data-notif-link");
          fetch(`/api/notifications/${id}/read`, { method: "POST" }).then(() => {
            loadTqNotifications();
            if (link) window.location.href = link;
          });
        });
      });
    })
    .catch((err) => console.error("Failed to load notifications", err));
}

function tqRenderNotifItem(n) {
  const color = TQ_CATEGORY_COLORS[n.category] || "#8A9BA0";
  const time = tqTimeAgo(n.created_at);
  return `
    <div class="tq-notif-item ${n.is_read ? "" : "unread"}" data-notif-id="${n.id}" data-notif-link="${n.link || ""}">
      <span class="tq-notif-dot" style="background:${color};"></span>
      <div>
        <div class="fw-semibold" style="font-size:0.83rem;">${tqEscapeHtml(n.title)}</div>
        <div class="text-muted" style="font-size:0.78rem;">${tqEscapeHtml(n.message)}</div>
        <div class="text-muted" style="font-size:0.7rem;">${time}</div>
      </div>
    </div>`;
}

function tqEscapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function tqTimeAgo(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
