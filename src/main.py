from typing import List
from flask import Flask
from liquidctl.driver.kraken3 import KrakenX3

app = Flask(__name__)

product_id = 8199
vendor_id = 7793
kraken = None


@app.route("/devices/kraken/status")
def get_kraken_status():
    global kraken
    if kraken is None:
        return {"error": "Kraken device is not initialize"}

    temp, speed, duty = kraken.get_status()

    return {"temp": temp, "speed": speed, "duty": duty}


@app.route("/devices/kraken/initialize")
def initialize_kraken():
    global kraken
    if kraken is None:
        kraken = get_kraken_x63()
    kraken.connect()
    return kraken.initialize()


@app.route("/devices/kraken/disconnect")
def disconnect_kraken():
    global kraken
    if kraken is None:
        return {"status": "device already disconnected"}
    kraken.disconnect()
    kraken = None
    return {"status": "disconnected"}


def find_kraken_devices() -> List[KrakenX3]:
    devices = KrakenX3.find_supported_devices()
    if not devices:
        raise RuntimeError("No Kraken device found.")
    return devices


def get_kraken_x63() -> KrakenX3:
    devices = find_kraken_devices()
    global kraken
    for device in devices:
        if product_id == device.product_id and vendor_id == device.vendor_id:
            kraken = device
            break

    if kraken is None:
        raise RuntimeError("X63 not found.")

    return kraken


# kraken: KrakenX3 = get_kraken_x63()


# if __name__ == "__main__":
#     from waitress import serve
#     serve(app, host="0.0.0.0", port=8080)
