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

// ── Lifecycle stage ────────────────────────────────────────────────────────
// Prefer the stage field from the API when present.
// Falls back to client-side calculation for seed data.
// Thresholds must match momentum.py get_lifecycle_stage().
function getLifecycleStage(n) {
  if (n.stage) return n.stage;
  const score    = n.confidence;
  const mentions = n.mentions_growth || 0;
  if (score < 55)                              return "declining";
  if (score < 68 && mentions >= 60)            return "emerging";
  if (score < 68)                              return "declining";
  if (score < 78)                              return "rising";
  return "peak";
}

function lifecycleArrow(stage) {
  const map = {
    emerging:  { arrow: "↗", color: "#38bdf8" },
    rising:    { arrow: "↑", color: "#10b981" },
    peak:      { arrow: "▲", color: "#f0b90b" },
    declining: { arrow: "↘", color: "#ef4444" },
  };
  return map[stage] || map.rising;
}

// ── Source label ───────────────────────────────────────────────────────────
function getSourceLabel(source) {
  const map = {
    live:           "LIVE",
    binance_square: "LIVE",
    demo:           "DEMO",
    seed:           "CACHED",
  };
  return map[source] || "LIVE";
}

// ── Leaderboard ────────────────────────────────────────────────────────────
function renderLeaderboard(narratives) {
  const container = document.getElementById("leaderboard");
  if (!container) return;
  container.innerHTML = "";

  const sorted = [...narratives].sort((a, b) => b.confidence - a.confidence);

  sorted.forEach((n, i) => {
    const theme = confidenceTheme(n.confidence);
    const stage = getLifecycleStage(n);
    const lc    = lifecycleArrow(stage);
    const isTop = i < 3;

    const row = document.createElement("div");
    row.className = "lb-row";
    row.style.setProperty("--lb-color", theme.color);
    row.style.animationDelay = `${i * 60}ms`;

    row.innerHTML = `
      <span class="lb-rank ${isTop ? "top" : ""}">${i + 1}</span>
      <div class="lb-info">
        <span class="lb-name">${n.name}</span>
        <span class="lb-tokens">${n.tokens.slice(0, 4).join(" · ")}</span>
      </div>
      <div class="lb-bar-wrap">
        <div class="lb-bar" style="width:${n.confidence}%;background:${theme.color}"></div>
      </div>
      <span class="lb-score" style="color:${theme.color}">
        ${n.confidence}<span style="font-size:11px;opacity:0.6">%</span>
        <span class="stage-item-arrow" style="color:${lc.color};font-size:13px;margin-left:4px">${lc.arrow}</span>
      </span>
    `;
    container.appendChild(row);
  });
}

// ── Lifecycle Tracker ──────────────────────────────────────────────────────
function renderLifecycle(narratives) {
  const stages = ["emerging", "rising", "peak", "declining"];

  stages.forEach(s => {
    const el = document.querySelector(`#stage-${s} .stage-items`);
    if (el) el.innerHTML = "";
  });

  narratives.forEach((n, i) => {
    const stage     = getLifecycleStage(n);
    const lc        = lifecycleArrow(stage);
    const container = document.querySelector(`#stage-${stage} .stage-items`);
    if (!container) return;

    const item = document.createElement("div");
    item.className = "stage-item";
    item.style.animationDelay = `${i * 50}ms`;
    item.innerHTML = `
      <span class="stage-item-name">${n.name}</span>
      <span class="stage-item-score" style="color:${lc.color}">${n.confidence}%</span>
      <span class="stage-item-arrow" style="color:${lc.color}">${lc.arrow} ${stage.toUpperCase()}</span>
    `;
    container.appendChild(item);
  });

  stages.forEach(s => {
    const el = document.querySelector(`#stage-${s} .stage-items`);
    if (el && el.children.length === 0) {
      el.innerHTML = `<div class="stage-item"><span class="stage-item-name" style="color:var(--muted)">—</span></div>`;
    }
  });
}

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
          titleFont: { family: "'DM Mono', monospace" },
          bodyFont:  { family: "'DM Mono', monospace", size: 10 },
          padding: 12,
        }
      },
      scales: {
        x: {
          ticks: { color: "#444", font: { family: "'DM Mono', monospace", size: 9 }, maxRotation: 30 },
          grid:  { color: "rgba(255,255,255,0.03)" },
        },
        y: {
          min: 0, max: 100,
          ticks: { color: "#444", font: { family: "'DM Mono', monospace", size: 9 }, callback: v => `${v}%` },
          grid:  { color: "rgba(255,255,255,0.03)" },
        }
      }
    }
  });
}

// ── Radar chart ────────────────────────────────────────────────────────────
function renderRadar(narratives) {
  const ctx = document.getElementById("tokenRadar").getContext("2d");
  if (radarChart) radarChart.destroy();

  const top = [...narratives].sort((a, b) => b.confidence - a.confidence).slice(0, 6);

  radarChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels: top.map(n => n.name),
      datasets: [{
        label: "Confidence",
        data: top.map(n => n.confidence),
        backgroundColor: "rgba(240,185,11,0.07)",
        borderColor: "rgba(240,185,11,0.5)",
        borderWidth: 1.5,
        pointBackgroundColor: top.map(n => confidenceTheme(n.confidence).color),
        pointRadius: 3,
        pointHoverRadius: 6,
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
          grid:        { color: "rgba(255,255,255,0.05)" },
          angleLines:  { color: "rgba(255,255,255,0.05)" },
          pointLabels: { color: "#888", font: { family: "'DM Mono', monospace", size: 11 } }
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

// ── Seed fallback data (used when API is cold-starting or unreachable) ──────
const SEED_NARRATIVES = [
  { name: "AI Infrastructure",    confidence: 84, mentions_growth: 91, engagement_growth: 88, volume_growth: 62, stage: "peak",      tokens: ["FET","TAO","RNDR","AKT","WLD","AGIX","OCEAN"], post_count: 47 },
  { name: "Solana Ecosystem",     confidence: 79, mentions_growth: 86, engagement_growth: 82, volume_growth: 57, stage: "peak",      tokens: ["SOL","JUP","RAY","BONK","PYTH","JTO","ORCA"],  post_count: 41 },
  { name: "Bitcoin Ecosystem",    confidence: 76, mentions_growth: 84, engagement_growth: 79, volume_growth: 53, stage: "peak",      tokens: ["STX","ORDI","SATS","RUNE","WBTC"],             post_count: 38 },
  { name: "DeFi Resurgence",      confidence: 71, mentions_growth: 77, engagement_growth: 72, volume_growth: 49, stage: "rising",    tokens: ["AAVE","UNI","CRV","GMX","DYDX","PENDLE"],      post_count: 33 },
  { name: "DePIN Compute",        confidence: 67, mentions_growth: 71, engagement_growth: 65, volume_growth: 58, stage: "emerging",  tokens: ["HNT","IOTX","FIL","AKT","AR","STORJ"],         post_count: 28 },
  { name: "Layer 2 Scaling",      confidence: 63, mentions_growth: 68, engagement_growth: 61, volume_growth: 44, stage: "declining", tokens: ["ARB","OP","MATIC","ZKS","STRK","MANTA"],       post_count: 24 },
  { name: "RWA Tokenization",     confidence: 58, mentions_growth: 62, engagement_growth: 55, volume_growth: 41, stage: "emerging",  tokens: ["ONDO","CFG","MPL","TRU","POLYX"],              post_count: 19 },
  { name: "Gaming Infrastructure",confidence: 52, mentions_growth: 55, engagement_growth: 49, volume_growth: 46, stage: "declining", tokens: ["IMX","RON","MAGIC","BEAM","GALA","SAND"],      post_count: 16 },
];

function renderAll(narratives, source, lastUpdated) {
  allNarratives = narratives;

  // Use the actual data timestamp — not the current time
  if (lastUpdatedEl) lastUpdatedEl.textContent = lastUpdated ? formatTime(lastUpdated) : "—";
  if (sourceTagEl)   sourceTagEl.textContent   = getSourceLabel(source);
  if (narrativeCount) narrativeCount.textContent = `${narratives.length} NARRATIVES`;

  renderLeaderboard(narratives);
  renderLifecycle(narratives);
  renderTimeline(narratives);
  renderRadar(narratives);
  renderHeatmap(narratives);
  renderCards(narratives);
}

// ── Main load ──────────────────────────────────────────────────────────────
async function loadNarratives(force = false) {
  setLoading(true);
  hideError();

  // 55s timeout to handle Render cold starts
  const controller = new AbortController();
  const timeout    = setTimeout(() => controller.abort(), 55000);

  try {
    const url  = force ? `${API}?refresh=true` : API;
    const resp = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);

    if (!resp.ok) throw new Error(`API error ${resp.status}`);

    const data = await resp.json();

    if (!data || !Array.isArray(data.narratives) || !data.narratives.length) {
      throw new Error("Empty response from API.");
    }

    renderAll(data.narratives, data.source, data.last_updated);

  } catch (err) {
    clearTimeout(timeout);
    console.warn("[Narratex] API unreachable — using seed data.", err.message);

    // Fall back to seed data — dashboard stays functional
    renderAll(SEED_NARRATIVES, "seed", null);

    if (sourceTagEl)   sourceTagEl.textContent   = "CACHED";
    if (lastUpdatedEl) lastUpdatedEl.textContent  = "—";
  } finally {
    setLoading(false);
  }
}

document.getElementById("refresh-btn")?.addEventListener("click", () => loadNarratives(true));
document.getElementById("retry-btn")?.addEventListener("click",   () => loadNarratives(false));

loadNarratives();
