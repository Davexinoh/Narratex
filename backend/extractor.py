import json

# Simple keyword based narrative mapping
NARRATIVE_KEYWORDS = {
    "AI Infrastructure": ["ai", "agent", "compute"],
    "DePIN Compute": ["storage", "compute", "decentralized"],
    "Gaming Infrastructure": ["game", "gaming", "nft"]
}

def load_market_signals():

    with open("data/market_signals.json", "r") as f:
        data = json.load(f)

    return data


def detect_narratives(signals):

    narratives = {}

    for narrative in NARRATIVE_KEYWORDS:
        narratives[narrative] = 0

    for token in signals:

        symbol = token["symbol"].lower()

        for narrative, keywords in NARRATIVE_KEYWORDS.items():

            for keyword in keywords:

                if keyword in symbol:
                    narratives[narrative] += 1

    return narratives


def save_narratives(narratives):

    output = []

    for name, score in narratives.items():

        narrative = {
            "name": name,
            "score": score
        }

        output.append(narrative)

    with open("data/narratives_raw.json", "w") as f:
        json.dump(output, f, indent=2)


def run():

    print("Loading signals...")

    signals = load_market_signals()

    narratives = detect_narratives(signals)

    save_narratives(narratives)

    print("Narratives extracted")


if __name__ == "__main__":
    run()
