const API = "https://narratex.onrender.com/api/narratives";

// Bug fix #4: Show loading state immediately
function setLoading(active) {
  document.getElementById("loading-overlay").style.display = active ? "flex" : "none";
}

// Bug fix #5: Map confidence score to a color on a green→yellow→red scale
function confidenceColor(score) {
  if (score >= 75) return { bg: "#10b981", text: "#fff" };       // strong — green
  if (score >= 50) return { bg: "#f0b90b", text: "#000" };       // moderate — amber
  return { bg: "#ef4444", text: "#fff" };                         // weak — red
}

// Bug fix #2: Build a real timeline chart from narrative data
function renderTimeline(narratives) {
  const ctx = document.getElementById("timelineChart").getContext("2d");

  const sorted = [...narratives].sort((a, b) => b.confidence - a.confidence);
  const labels = sorted.map(n => n.name);
  const scores = sorted.map(n => n.confidence);
  const colors = scores.map(s => confidenceColor(s).bg);

  new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Narrative Momentum Score",
        data: scores,
        backgroundColor: colors,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#94a3b8", font: { family: "'IBM Plex Mono', monospace" } } },
        tooltip: {
          callbacks: {
            label: ctx => ` Confidence: ${ctx.parsed.y}%`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#94a3b8", font: { family: "'IBM Plex Mono', monospace" } },
          grid: { color: "rgba(148,163,184,0.08)" }
        },
        y: {
          min: 0,
          max: 100,
          ticks: {
            color: "#94a3b8",
            font: { family: "'IBM Plex Mono', monospace" },
            callback: val => `${val}%`
          },
          grid: { color: "rgba(148,163,184,0.08)" }
        }
      }
    }
  });
}

// Bug fix #3: Deduplicate tokens and cap radar to top 10 for readability
function renderRadar(narratives) {
  const tokenMap = {};

  narratives.forEach(n => {
    n.tokens.forEach(token => {
      if (!tokenMap[token] || tokenMap[token] < n.confidence) {
        tokenMap[token] = n.confidence;
      }
    });
  });

  const sorted = Object.entries(tokenMap).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const labels = sorted.map(e => e[0]);
  const scores = sorted.map(e => e[1]);

  const ctx = document.getElementById("tokenRadar").getContext("2d");

  new Chart(ctx, {
    type: "radar",
    data: {
      labels,
      datasets: [{
        label: "Token Narrative Strength",
        data: scores,
        backgroundColor: "rgba(240,185,11,0.15)",
        borderColor: "#f0b90b",
        pointBackgroundColor: "#f0b90b",
        pointBorderColor: "#fff",
        pointHoverBackgroundColor: "#fff",
        pointHoverBorderColor: "#f0b90b"
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#94a3b8", font: { family: "'IBM Plex Mono', monospace" } } }
      },
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: {
            color: "#64748b",
            backdropColor: "transparent",
            font: { family: "'IBM Plex Mono', monospace", size: 10 },
            callback: val => `${val}%`
          },
          grid: { color: "rgba(148,163,184,0.1)" },
          pointLabels: {
            color: "#cbd5e1",
            font: { family: "'IBM Plex Mono', monospace", size: 11 }
          }
        }
      }
    }
  });
}

function renderHeatmap(narratives) {
  const heatmap = document.getElementById("heatmap");
  heatmap.innerHTML = "";

  // Bug fix #5: Color each cell based on confidence level
  narratives.forEach(n => {
    const { bg, text } = confidenceColor(n.confidence);
    const heat = document.createElement("div");
    heat.className = "heat";
    heat.style.background = bg;
    heat.style.color = text;
    heat.innerHTML = `
      <span class="heat-name">${n.name}</span>
      <span class="heat-score">${n.confidence}%</span>
    `;
    heatmap.appendChild(heat);
  });
}

function renderCards(narratives) {
  const container = document.getElementById("cards");
  container.innerHTML = "";

  narratives.forEach(n => {
    const { bg } = confidenceColor(n.confidence);
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card-header">
        <h3>${n.name}</h3>
        <span class="badge" style="background:${bg}">${n.confidence}%</span>
      </div>
      <p class="card-label">Tokens</p>
      <div class="token-list">
        ${n.tokens.map(t => `<span class="token-tag">${t}</span>`).join("")}
      </div>
    `;
    container.appendChild(card);
  });
}

async function loadNarratives() {
  setLoading(true);

  try {
    // Bug fix #1: Wrap in try/catch so API failures don't crash the page
    const response = await fetch(API);

    if (!response.ok) {
      throw new Error(`API responded with status ${response.status}`);
    }

    const data = await response.json();

    // Bug fix #6: Guard against missing or malformed data shape
    if (!data || !Array.isArray(data.narratives) || data.narratives.length === 0) {
      throw new Error("No narrative data returned from API.");
    }

    const narratives = data.narratives;

    renderTimeline(narratives);
    renderRadar(narratives);
    renderHeatmap(narratives);
    renderCards(narratives);

  } catch (err) {
    console.error("Narratex load error:", err);
    document.getElementById("error-banner").style.display = "flex";
    document.getElementById("error-message").textContent = err.message || "Unknown error.";
  } finally {
    setLoading(false);
  }
}

loadNarratives();
