const API_URL = "https://narratex.onrender.com/api/narratives"

fetch(API_URL)

.then(response => response.json())

.then(data => {

const container = document.getElementById("cards")
const heatmap = document.getElementById("heatmap")

container.innerHTML = ""
heatmap.innerHTML = ""

let tokenLabels = []
let tokenScores = []

data.narratives.forEach(narrative => {

const card = document.createElement("div")

card.className = "card"

card.innerHTML = `
<h3>${narrative.name}</h3>
<p>Confidence: ${narrative.confidence}%</p>
<p>Tokens: ${narrative.tokens.join(", ")}</p>
`

container.appendChild(card)

const heat = document.createElement("div")

heat.className = "heat"

heat.innerHTML = `${narrative.name} — ${narrative.confidence}%`

heatmap.appendChild(heat)

narrative.tokens.forEach(token => {

tokenLabels.push(token)
tokenScores.push(narrative.confidence)

})

})

const radar = document.getElementById("tokenRadar")

new Chart(radar, {

type: "radar",

data: {

labels: tokenLabels,

datasets: [{

label: "Token Narrative Strength",

data: tokenScores,

backgroundColor: "rgba(240,185,11,0.2)",

borderColor: "#f0b90b"

}]

}

})

})
