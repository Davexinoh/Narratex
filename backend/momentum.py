import json

def load_raw_narratives():

    with open("data/narratives_raw.json", "r") as f:
        data = json.load(f)

    return data


def calculate_confidence(score):

    confidence = min(score * 20, 100)

    return confidence


def detect_early_signal(score):

    if score >= 4:
        return "Strong Narrative"
    elif score >= 2:
        return "Emerging Narrative"
    else:
        return "Weak Signal"


def attach_tokens(narrative):

    token_map = {
        "AI Infrastructure": ["FET","TAO","RNDR","AKT"],
        "DePIN Compute": ["FIL","AR","STORJ"],
        "Gaming Infrastructure": ["IMX","RON","MAGIC"]
    }

    return token_map.get(narrative, [])


def build_predictions(raw_narratives):

    predictions = []

    for item in raw_narratives:

        name = item["name"]
        score = item["score"]

        confidence = calculate_confidence(score)

        prediction = {
            "name": name,
            "confidence": confidence,
            "signal": detect_early_signal(score),
            "tokens": attach_tokens(name)
        }

        predictions.append(prediction)

    return predictions


def save_predictions(predictions):

    output = {"narratives": predictions}

    with open("data/narratives.json", "w") as f:
        json.dump(output, f, indent=2)


def run():

    print("Calculating narrative momentum...")

    raw = load_raw_narratives()

    predictions = build_predictions(raw)

    save_predictions(predictions)

    print("Narrative predictions updated")


if __name__ == "__main__":
    run()
