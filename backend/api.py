from flask import Flask, jsonify
import json
import os

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "narratives.json")

@app.route("/")
def home():

    return {
        "status": "ok",
        "service": "Narratex API"
    }

@app.route("/api/narratives")
def narratives():

    try:

        with open(DATA_PATH, "r") as f:
            data = json.load(f)

        return jsonify(data)

    except Exception as e:

        return jsonify({
            "error": "unable to load narratives",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
