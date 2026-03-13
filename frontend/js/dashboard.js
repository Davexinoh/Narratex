fetch("http://localhost:10000/api/narratives")
.then(response => response.json())
.then(data => {

if(!data.narratives){
throw new Error("Invalid API response")
}

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
<h2>${narrative.name}</h2>
<p><strong>Confidence:</strong> ${narrative.confidence}%</p>
<p><strong>Signal:</strong> ${narrative.signal}</p>
<p><strong>Tokens:</strong> ${narrative.tokens.join(", ")}</p>
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
.catch(err => {

document.getElementById("cards").innerHTML =
"<p>Unable to load Narratex data</p>"

console.error(err)

})
