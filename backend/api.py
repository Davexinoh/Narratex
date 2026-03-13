from flask import Flask, jsonify
import json

app = Flask(__name__)


@app.route("/")
def home():

    return {
        "message": "Narratex API is running"
    }


@app.route("/api/narratives")
def narratives():

    with open("data/narratives.json", "r") as f:

        data = json.load(f)

    return jsonify(data)


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=10000)
