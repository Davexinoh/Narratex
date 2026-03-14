const API = "https://narratex.onrender.com/api/narratives";

// ── State ──────────────────────────────────────────────────────────────────
let allNarratives = [];
let activeFilter  = "all";
let timelineChart = null;
let radarChart    = null;

// ── DOM refs ───────────────────────────────────────────────────────────────
const loadingOverlay = document.getElementById("loading-overlay");
const errorBanner    = document.getElementById("error-banner");
const errorMessage   = document.getElementById("error-message");
const lastUpdatedEl  = document.getElementById("last-updated");
const sourceTagEl    = document.getElementById("source-tag");
const narrativeCount = document.getElementById("narrative-count");

// ── Helpers ────────────────────────────────────────────────────────────────
function confidenceTheme(score) {
  if (score >= 75) return { color: "#10b981", label: "STRONG",   glow: "rgba(16,185,129,0.12)"  };
  if (score >= 50) return { color: "#f0b90b", label: "MODERATE", glow: "rgba(240,185,11,0.1)"   };
  return              { color: "#ef4444", label: "WEAK",     glow: "rgba(239,68,68,0.1)"    };
}

function formatTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function setLoading(on) {
  loadingOverlay.style.display = on ? "flex" : "none";
}

function showError(msg) {
  errorBanner.style.display = "flex";
  errorMessage.textContent  = msg;
}

function hideError() {
  errorBanner.style.display = "none";
}

// ── Chart defaults ─────────────────────────────────────────────────────────
const CHART_DEFAULTS = {
  color: "#555",
  font: { family: "'DM Mono', monospace", size: 10 },
};

// ── Timeline / Bar chart ───────────────────────────────────────────────────
function renderTimeline(narratives) {
  const ctx = document.getElementById("timelineChart").getContext("2d");
  if (timelineChart) timelineChart.destroy();

  const sorted = [...narratives].sort((a, b) => b.confidence - a.confidence);

  timelineChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: sorted.map(n => n.name),
      datasets: [
        {
          label: "Confidence",
          data: sorted.map(n => n.confidence),
          backgroundColor: sorted.map(n => confidenceTheme(n.confidence).color + "22"),
          borderColor:     sorted.map(n => confidenceTheme(n.confidence).color),
          borderWidth: 1,
          borderRadius: 0,
          borderSkipped: false,
        },
        {
          label: "Mentions",
          data: sorted.map(n => n.mentions_growth || 0),
          backgroundColor: "rgba(255,255,255,0.04)",
          borderColor: "rgba(255,255,255,0.12)",
          borderWidth: 1,
          borderRadius: 0,
          borderSkipped: false,
        },
        {
          label: "Engagement",
          data: sorted.map(n => n.engagement_growth || 0),
          backgroundColor: "rgba(240,185,11,0.06)",
          borderColor: "rgba(240,185,11,0.2)",
          borderWidth: 1,
          borderRadius: 0,
          borderSkipped: false,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          labels: {
            color: "#555",
            font: { family: "'DM Mono', monospace", size: 10 },
            boxWidth: 10,
            padding: 16,
          }
        },
        tooltip: {
          backgroundColor: "#0d0d0d",
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 1,
          titleColor: "#fff",
          bodyColor: "#888",
          titleFont: { family: "'DM Mono', monospace", size: 11 },
          bodyFont:  { family: "'DM Mono', monospace", size: 10 },
          padding: 12,
          callbacks: { label: c => `  ${c.dataset.label}: ${c.parsed.y}%` }
        }
      },
      scales: {
        x: {
          ticks: { color: "#444", font: { family: "'DM Mono', monospace", size: 9 }, maxRotation: 28 },
          grid:  { color: "rgba(255,255,255,0.03)" }
        },
        y: {
          min: 0, max: 100,
          ticks: { color: "#444", font: { family: "'DM Mono', monospace", size: 9 }, callback: v => `${v}%` },
          grid:  { color: "rgba(255,255,255,0.03)" }
        }
      }
    }
  });
}

// ── Radar chart ────────────────────────────────────────────────────────────
function renderRadar(narratives) {
  const ctx = document.getElementById("tokenRadar").getContext("2d");
  if (radarChart) radarChart.destroy();

  const tokenMap = {};
  narratives.forEach(n => {
    n.tokens.forEach(t => {
      if (!tokenMap[t] || tokenMap[t] < n.confidence) tokenMap[t] = n.confidence;
    });
  });

  const top = Object.entries(tokenMap).sort((a,b) => b[1]-a[1]).slice(0,10);

  radarChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels: top.map(e => e[0]),
      datasets: [{
        label: "Narrative Strength",
        data:  top.map(e => e[1]),
        backgroundColor:    "rgba(240,185,11,0.06)",
        borderColor:        "#f0b90b",
        borderWidth:        1.5,
        pointBackgroundColor: "#f0b90b",
        pointBorderColor:   "#000",
        pointBorderWidth:   2,
        pointRadius:        4,
        pointHoverRadius:   6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          labels: { color: "#555", font: { family: "'DM Mono', monospace", size: 10 }, boxWidth: 10 }
        },
        tooltip: {
          backgroundColor: "#0d0d0d",
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 1,
          titleColor: "#fff",
          bodyColor: "#888",
          titleFont: { family: "'DM Mono', monospace" },
          bodyFont:  { family: "'DM Mono', monospace", size: 10 },
          padding: 12,
          callbacks: { label: c => `  Score: ${c.parsed.r}%` }
        }
      },
      scales: {
        r: {
          min: 0, max: 100,
          ticks: {
            color: "#333",
            backdropColor: "transparent",
            font: { family: "'DM Mono', monospace", size: 9 },
            callback: v => `${v}%`,
            stepSize: 25,
          },
          grid:       { color: "rgba(255,255,255,0.05)" },
          angleLines: { color: "rgba(255,255,255,0.05)" },
          pointLabels: {
            color: "#888",
            font: { family: "'DM Mono', monospace", size: 11 }
          }
        }
      }
    }
  });
}

// ── Heatmap ────────────────────────────────────────────────────────────────
function renderHeatmap(narratives) {
  const heatmap = document.getElementById("heatmap");
  heatmap.innerHTML = "";

  narratives.forEach((n, i) => {
    const theme = confidenceTheme(n.confidence);
    const cell  = document.createElement("div");
    cell.className = "heat";
    cell.style.setProperty("--glow-color", theme.glow);
    cell.style.animationDelay = `${i * 55}ms`;

    cell.innerHTML = `
      <div class="heat-top">
        <span class="heat-name">${n.name}</span>
        <span class="heat-badge" style="background:${theme.color}18;color:${theme.color};border:1px solid ${theme.color}30">${theme.label}</span>
      </div>
      <div class="heat-score" style="color:${theme.color}">${n.confidence}<span class="heat-pct">%</span></div>
      <div class="heat-track">
        <div class="heat-fill" style="width:${n.confidence}%;background:${theme.color}"></div>
      </div>
    `;
    heatmap.appendChild(cell);
  });
}

// ── Cards ──────────────────────────────────────────────────────────────────
function renderCards(narratives) {
  const container = document.getElementById("cards");
  container.innerHTML = "";

  const filtered = narratives.filter(n => {
    if (activeFilter === "strong")   return n.confidence >= 75;
    if (activeFilter === "moderate") return n.confidence >= 50 && n.confidence < 75;
    if (activeFilter === "weak")     return n.confidence < 50;
    return true;
  });

  if (!filtered.length) {
    container.innerHTML = `<p class="empty-state">No narratives match this filter.</p>`;
    return;
  }

  filtered.forEach((n, i) => {
    const theme = confidenceTheme(n.confidence);
    const card  = document.createElement("div");
    card.className = "card";
    card.style.animationDelay = `${i * 70}ms`;
    card.style.setProperty("--card-accent", theme.color);

    card.innerHTML = `
      <div class="card-header">
        <h3 class="card-title">${n.name}</h3>
        <span class="card-badge" style="color:${theme.color};background:${theme.color}15">${n.confidence}%</span>
      </div>
      <div class="signals">
        <div class="sig-row">
          <span class="sig-label">Mentions</span>
          <div class="sig-track"><div class="sig-fill" style="width:${n.mentions_growth||0}%;background:#38bdf8"></div></div>
          <span class="sig-val">${n.mentions_growth||0}%</span>
        </div>
        <div class="sig-row">
          <span class="sig-label">Engagement</span>
          <div class="sig-track"><div class="sig-fill" style="width:${n.engagement_growth||0}%;background:#a78bfa"></div></div>
          <span class="sig-val">${n.engagement_growth||0}%</span>
        </div>
        <div class="sig-row">
          <span class="sig-label">Volume</span>
          <div class="sig-track"><div class="sig-fill" style="width:${n.volume_growth||0}%;background:#f0b90b"></div></div>
          <span class="sig-val">${n.volume_growth||0}%</span>
        </div>
      </div>
      <div class="card-rule"></div>
      <span class="token-label">Tokens</span>
      <div class="token-list">${n.tokens.map(t => `<span class="token-tag">${t}</span>`).join("")}</div>
    `;
    container.appendChild(card);
  });
}

// ── Filter buttons ─────────────────────────────────────────────────────────
document.querySelectorAll(".fbtn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".fbtn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.filter;
    renderCards(allNarratives);
  });
});

// ── Main load ──────────────────────────────────────────────────────────────
async function loadNarratives(force = false) {
  setLoading(true);
  hideError();

  try {
    const url  = force ? `${API}?refresh=true` : API;
    const resp = await fetch(url);

    if (!resp.ok) throw new Error(`API error ${resp.status}: ${resp.statusText}`);

    const data = await resp.json();

    if (!data || !Array.isArray(data.narratives) || !data.narratives.length) {
      throw new Error("No narrative data returned from API.");
    }

    allNarratives = data.narratives;

    if (lastUpdatedEl)  lastUpdatedEl.textContent  = formatTime(data.last_updated);
    if (sourceTagEl)    sourceTagEl.textContent     = data.source === "demo" ? "DEMO" : "LIVE";
    if (narrativeCount) narrativeCount.textContent  = `${allNarratives.length} NARRATIVES`;

    renderTimeline(allNarratives);
    renderRadar(allNarratives);
    renderHeatmap(allNarratives);
    renderCards(allNarratives);

  } catch (err) {
    console.error("[Narratex]", err);
    showError(err.message || "Failed to load data.");
  } finally {
    setLoading(false);
  }
}

document.getElementById("refresh-btn")?.addEventListener("click", () => loadNarratives(true));
document.getElementById("retry-btn")?.addEventListener("click",   () => loadNarratives(false));

loadNarratives();
