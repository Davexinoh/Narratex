import requests
import json

BINANCE_API = "https://api.binance.com/api/v3/ticker/24hr"

def fetch_market_data():

    response = requests.get(BINANCE_API)
    data = response.json()

    signals = []

    for token in data[:20]:

        signal = {
            "symbol": token["symbol"],
            "priceChangePercent": float(token["priceChangePercent"]),
            "volume": float(token["volume"])
        }

        signals.append(signal)

    return signals


def save_signals(signals):

    with open("data/market_signals.json", "w") as f:
        json.dump(signals, f, indent=2)


def run():

    print("Collecting market signals...")

    signals = fetch_market_data()

    save_signals(signals)

    print("Signals saved")


if __name__ == "__main__":

    run()
