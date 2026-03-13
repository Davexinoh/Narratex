fetch("../data/narratives.json")
.then(response => response.json())
.then(data => {

const container = document.getElementById("cards")

data.narratives.forEach(narrative => {

const card = document.createElement("div")
card.className = "card"

card.innerHTML = `
<h2>${narrative.name}</h2>

<p><strong>Confidence:</strong> ${narrative.confidence}%</p>

<p><strong>Mentions Growth:</strong> ${narrative.mentions_growth}%</p>

<p><strong>Dev Activity:</strong> ${narrative.dev_growth}%</p>

<p><strong>Volume Growth:</strong> ${narrative.volume_growth}%</p>

<p><strong>Tokens:</strong> ${narrative.tokens.join(", ")}</p>
`

container.appendChild(card)

})

})

const ctx = document.getElementById("timelineChart")

new Chart(ctx, {

type: "line",

data: {

labels: ["10:00","11:00","12:00","13:00"],

datasets: [{
label: "AI Infrastructure Mentions",

data: [80,110,160,210],

borderColor: "#f0b90b",
backgroundColor: "rgba(240,185,11,0.2)",

tension: 0.4
}]

},

options: {

responsive: true

}

})
