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

// ── Lifecycle stage assignment ─────────────────────────────────────────────
// Uses API stage field if present. Falls back to relative scoring within
// the current dataset so distribution is always balanced across stages.
function getLifecycleStage(n) {
  // Always trust the API stage field first
  if (n.stage && ["emerging","rising","peak","declining"].includes(n.stage)) {
    return n.stage;
  }

  // Client-side fallback — relative percentile within current dataset
  const scores  = allNarratives.map(x => x.confidence);
  const max     = Math.max(...scores) || 100;
  const min     = Math.min(...scores) || 0;
  const range   = max - min || 1;
  const pct     = ((n.confidence - min) / range) * 100;
  const mentions = n.mentions_growth || 0;

  if (pct >= 75)                    return "peak";
  if (pct >= 50 && mentions >= 55)  return "rising";
  if (pct >= 25 && mentions >= 40)  return "emerging";
  if (pct >= 50)                    return "rising";
  return "declining";
}

function lifecycleArrow(stage) {
  const map = {
    emerging:  { arrow: "↗",  color: "#38bdf8" },
    rising:    { arrow: "↑",  color: "#10b981" },
    peak:      { arrow: "▲",  color: "#f0b90b" },
    declining: { arrow: "↘",  color: "#ef4444" },
  };
  return map[stage] || map.rising;
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

  // Clear all stage item containers
  stages.forEach(s => {
    const el = document.querySelector(`#stage-${s} .stage-items`);
    if (el) el.innerHTML = "";
  });

  narratives.forEach((n, i) => {
    const stage = getLifecycleStage(n);
    const lc    = lifecycleArrow(stage);
    const theme = confidenceTheme(n.confidence);
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

  // Show empty state for any stage with no narratives
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

// ── Capital Rotation Radar ─────────────────────────────────────────────────
function renderRotation(narratives) {
  const container = document.getElementById("rotation-radar");
  if (!container) return;
  container.innerHTML = "";

  // Derive rotation by comparing confidence + mentions across sorted narratives
  // Narratives are already sorted by confidence desc from the API
  // Rotation = capital flowing FROM lower-momentum → TO higher-momentum narratives
  const sorted = [...narratives].sort((a, b) => b.confidence - a.confidence);

  // Build rotation pairs: top gainers absorbing from bottom losers
  const gainers  = sorted.filter(n => getLifecycleStage(n) === "peak" || getLifecycleStage(n) === "rising");
  const losers   = sorted.filter(n => getLifecycleStage(n) === "declining");
  const emerging = sorted.filter(n => getLifecycleStage(n) === "emerging");

  // Flow arrows: losers → gainers
  const flows = [];
  losers.forEach((loser, i) => {
    const target = gainers[i % gainers.length];
    if (target) flows.push({ from: loser, to: target, strength: loser.confidence });
  });
  // Emerging absorbing from mid-tier
  emerging.forEach(e => {
    const mid = sorted.find(n =>
      getLifecycleStage(n) === "rising" && n.name !== e.name
    );
    if (mid) flows.push({ from: mid, to: e, strength: Math.round(e.mentions_growth || 50) });
  });

  if (!flows.length) {
    container.innerHTML = `<p class="empty-state">Insufficient data to detect rotation patterns.</p>`;
    return;
  }

  // Overall rotation summary bar
  const summaryEl = document.createElement("div");
  summaryEl.className = "rotation-summary";
  summaryEl.innerHTML = `
    <div class="rotation-summary-inner">
      <span class="rotation-label">CAPITAL FLOW DIRECTION</span>
      <div class="rotation-flow-bar">
        <span class="flow-from">DECLINING SECTORS</span>
        <span class="flow-arrow-big">→</span>
        <span class="flow-to">RISING SECTORS</span>
      </div>
    </div>
  `;
  container.appendChild(summaryEl);

  // Individual flow rows
  const flowsEl = document.createElement("div");
  flowsEl.className = "rotation-flows";

  flows.slice(0, 6).forEach((flow, i) => {
    const fromTheme = confidenceTheme(flow.from.confidence);
    const toTheme   = confidenceTheme(flow.to.confidence);
    const row = document.createElement("div");
    row.className = "rotation-row";
    row.style.animationDelay = `${i * 80}ms`;
    row.innerHTML = `
      <div class="rotation-from">
        <span class="rn-name" style="color:${fromTheme.color}">${flow.from.name}</span>
        <span class="rn-score" style="color:${fromTheme.color}">${flow.from.confidence}%</span>
        <span class="rn-stage">↘ ${getLifecycleStage(flow.from).toUpperCase()}</span>
      </div>
      <div class="rotation-arrow">
        <div class="arrow-line"></div>
        <span class="arrow-head">▶</span>
        <span class="arrow-label">${flow.strength}% signal</span>
      </div>
      <div class="rotation-to">
        <span class="rn-name" style="color:${toTheme.color}">${flow.to.name}</span>
        <span class="rn-score" style="color:${toTheme.color}">${flow.to.confidence}%</span>
        <span class="rn-stage">↑ ${getLifecycleStage(flow.to).toUpperCase()}</span>
      </div>
    `;
    flowsEl.appendChild(row);
  });

  container.appendChild(flowsEl);
}

// ── Narrative Token Map ────────────────────────────────────────────────────
function renderTokenMap(narratives) {
  const container = document.getElementById("token-map");
  if (!container) return;
  container.innerHTML = "";

  const grid = document.createElement("div");
  grid.className = "token-map-grid";

  narratives.forEach((n, i) => {
    const theme = confidenceTheme(n.confidence);
    const stage = getLifecycleStage(n);
    const lc    = lifecycleArrow(stage);

    const card = document.createElement("div");
    card.className = "tm-card";
    card.style.animationDelay = `${i * 60}ms`;
    card.style.setProperty("--tm-color", theme.color);

    card.innerHTML = `
      <div class="tm-header">
        <span class="tm-name">${n.name}</span>
        <span class="tm-badge" style="color:${lc.color}">${lc.arrow} ${stage.toUpperCase()}</span>
      </div>
      <div class="tm-confidence" style="color:${theme.color}">${n.confidence}%</div>
      <div class="tm-tokens">
        ${n.tokens.map((t, ti) => `
          <span class="tm-token" style="animation-delay:${(i * 60) + (ti * 30)}ms">${t}</span>
        `).join("")}
      </div>
      <div class="tm-bar">
        <div class="tm-bar-fill" style="width:${n.confidence}%;background:${theme.color}"></div>
      </div>
    `;
    grid.appendChild(card);
  });

  container.appendChild(grid);
}

// ── Narrative Predictions ──────────────────────────────────────────────────
// Derives prediction probability from signal acceleration:
// narratives with high mentions but lower confidence = building momentum = likely to emerge
function renderPredictions(narratives) {
  const container = document.getElementById("predictions");
  if (!container) return;
  container.innerHTML = "";

  // Score each narrative for "emergence potential"
  // High mentions_growth relative to confidence = undervalued narrative gaining traction
  const predictions = narratives.map(n => {
    const mentionsScore  = n.mentions_growth    || 0;
    const engagementScore = n.engagement_growth || 0;
    const confidence     = n.confidence;

    // Acceleration signal: momentum signals outpacing current confidence
    const avgSignal  = (mentionsScore + engagementScore) / 2;
    const gap        = avgSignal - confidence;
    const velocity   = Math.max(0, gap);

    // Probability = base confidence + velocity bonus, normalized to 40-95 range
    const rawProb    = confidence * 0.5 + velocity * 0.5;
    const probability = Math.min(95, Math.max(40, Math.round(rawProb)));

    const strength =
      probability >= 75 ? "STRONG" :
      probability >= 60 ? "MODERATE" : "SPECULATIVE";

    return { ...n, probability, velocity: Math.round(velocity), strength };
  })
  .sort((a, b) => b.probability - a.probability);

  // Header row
  const header = document.createElement("div");
  header.className = "pred-header";
  header.innerHTML = `
    <span class="pred-header-label">PREDICTED NARRATIVES</span>
    <sp
