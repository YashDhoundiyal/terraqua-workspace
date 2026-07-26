// Renders every <canvas data-chart="kind"> on the page by fetching /api/charts/<kind>
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("canvas[data-chart]").forEach((canvas) => {
    const kind = canvas.getAttribute("data-chart");
    fetch(`/api/charts/${kind}`)
      .then((r) => r.json())
      .then((payload) => renderTqChart(canvas, payload))
      .catch((err) => console.error("Chart load failed:", kind, err));
  });
});

function renderTqChart(canvas, payload) {
  if (!payload || !payload.datasets) return;
  const isDoughnut = payload.type === "doughnut";

  new Chart(canvas.getContext("2d"), {
    type: payload.type,
    data: { labels: payload.labels, datasets: payload.datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: {
          display: isDoughnut,
          position: "bottom",
          labels: { boxWidth: 10, font: { size: 11, family: "Inter" }, padding: 12 },
        },
      },
      scales: isDoughnut
        ? {}
        : {
            y: { beginAtZero: true, ticks: { precision: 0, font: { size: 11 } }, grid: { color: "#EEF1F1" } },
            x: { ticks: { font: { size: 11 } }, grid: { display: false } },
          },
    },
  });
}
