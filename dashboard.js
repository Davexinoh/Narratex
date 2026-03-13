const API = "https://narratex.onrender.com/api/narratives"

async function loadNarratives(){

const response = await fetch(API)

const data = await response.json()

const container = document.getElementById("cards")
const heatmap = document.getElementById("heatmap")

container.innerHTML = ""
heatmap.innerHTML = ""

let tokenLabels = []
let tokenScores = []

data.narratives.forEach(n => {

const card = document.createElement("div")

card.className = "card"

card.innerHTML = `
<h3>${n.name}</h3>
<p>Confidence: ${n.confidence}%</p>
<p>Tokens: ${n.tokens.join(", ")}</p>
`

container.appendChild(card)

const heat = document.createElement("div")

heat.className = "heat"

heat.innerHTML = `${n.name} — ${n.confidence}%`

heatmap.appendChild(heat)

n.tokens.forEach(token => {

tokenLabels.push(token)
tokenScores.push(n.confidence)

})

})

const radar = document.getElementById("tokenRadar")

new Chart(radar,{
type:"radar",
data:{
labels:tokenLabels,
datasets:[{
label:"Token Narrative Strength",
data:tokenScores,
backgroundColor:"rgba(240,185,11,0.2)",
borderColor:"#f0b90b"
}]
}
})

}

loadNarratives()
