import logging
from typing import Any, List

from flask import Flask, jsonify, request
from liquidctl.driver.kraken3 import _ANIMATION_SPEEDS, _COLOR_MODES, KrakenX3
from liquidctl.error import LiquidctlError

log = logging.getLogger(__name__)
# logging.basicConfig(filename="myapp.log", level=logging.INFO)

app = Flask(__name__)
# app.logger.setLevel(logging.ERROR)


class KrakenDevice:
    id: int
    description: str | None
    vendor_id: int | None
    product_id: int | None
    serial_number: str | None
    bus: str | None
    port: int | None
    address: str | None
    release_number: int | None
    color_channels: dict | None
    speed_channels: dict | None
    # (mode, size/variant, speed scale, min colors, max colors)
    color_modes = {k: v for k, v in _COLOR_MODES.items() if "backwards" not in k}
    animation_speeds = _ANIMATION_SPEEDS

    def __init__(
        self,
        id: int,
        description: str | None,
        vendor_id: int | None,
        product_id: int | None,
        serial_number: str | None,
        bus: str | None,
        port: int | None,
        address: str | None,
        release_number: int | None,
        color_channels: dict | None,
        speed_channels: dict | None,
    ):

        self.id = id
        self.description = description
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.serial_number = serial_number
        self.bus = bus
        self.port = port
        self.address = address
        self.release_number = release_number
        self.color_channels = color_channels
        self.speed_channels = speed_channels

    def to_dict(self) -> dict[str, str | int | Any]:
        return {
            "id": self.id,
            "description": self.description,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "serial_number": self.serial_number,
            "bus": self.bus,
            "port": self.port,
            "address": self.address,
            "release_number": self.release_number,
            "color_channels": self.color_channels,
            "speed_channels": self.speed_channels,
            "color_modes": self.color_modes,
            "animation_speeds": self.animation_speeds,
        }


class KrakenService:
    devices: dict[int, KrakenX3] = {}

    def __init__(self, arg=None):
        self.arg = arg

    def get_kraken_devices(self) -> list[KrakenDevice]:
        devices: list[KrakenDevice] = []
        if self.devices:
            return [
                KrakenDevice(
                    index,
                    device.description,
                    device.vendor_id,
                    device.product_id,
                    device.serial_number,
                    device.bus,
                    device.port,
                    device.address,
                    device.release_number,
                    color_channels=getattr(device, "_color_channels", {}),
                    speed_channels=getattr(device, "_speed_channels", {}),
                )
                for index, device in self.devices.items()
            ]

        try:
            found_devices = KrakenX3.find_supported_devices()
            for index, device in enumerate(found_devices):
                self.devices[index] = device
                self.__connect(device)
                devices.append(
                    KrakenDevice(
                        index,
                        device.description,
                        device.vendor_id,
                        device.product_id,
                        device.serial_number,
                        device.bus,
                        device.port,
                        device.address,
                        device.release_number,
                        color_channels=getattr(device, "_color_channels", {}),
                        speed_channels=getattr(device, "_speed_channels", {}),
                    )
                )
            return devices

        except ValueError:
            log.info("no kraken device found")
            return []

    def __connect(self, device: KrakenX3) -> None:
        try:

            device.connect()
            log.info(f"{device.description} connected")
        except RuntimeError as e:
            if "already open" in str(e):
                log.warning(f"{device.description} already open")
            else:
                log.error("unspecified liquidctl error")
                raise LiquidctlError from e

    def initialize_device(self, id: int):
        if self.devices.get(id) is None:
            return None
        device: KrakenX3 = self.devices[id]
        try:
            return device.initialize()
        except Exception as e:
            raise e

    def get_device_status(self, id: int):
        if self.devices.get(id) is None:
            return None
        device: KrakenX3 = self.devices[id]
        try:
            return device.get_status()
        except Exception as e:
            raise e

    def set_device_color(
        self,
        id: int,
        channel: str,
        mode: str,
        colors: List[List[int]],
        speed: str = "normal",
        direction: str = "forward",
    ):
        if self.devices.get(id) is None:
            return None
        device: KrakenX3 = self.devices[id]
        try:
            # channel, mode, colors, speed="normal", direction="forward"
            device.set_color(channel, mode, colors, speed, direction)
        except Exception as e:
            raise e

    def set_speed_profile(
        self, id: int, channel: str, profile: List[tuple[int, int]]
    ) -> bool:
        if self.devices.get(id) is None:
            return False
        device: KrakenX3 = self.devices[id]
        try:
            a = device.set_speed_profile(channel, profile)
            print(a)
            return True
        except Exception as e:
            raise e


kraken_service = KrakenService()


@app.route("/devices", methods=["GET"])
def get_devices():
    devices = [device.to_dict() for device in kraken_service.get_kraken_devices()]
    if devices is None:
        return {"status": "no devices found"}, 404
    return jsonify(devices), 200


@app.route("/devices/<int:id>/initialize", methods=["GET"])
def get_initialize(id: int):
    status = kraken_service.initialize_device(id)
    if status is None:
        return {f"status": "can't get initialize device with id: {id}"}, 404
    firmware, logo, ring = status
    return {"firmware": firmware, "logo": logo, "ring": ring}, 200


@app.route("/devices/<int:id>/status", methods=["GET"])
def get_status(id: int):
    status = kraken_service.get_device_status(id)
    if status is None:
        return {f"status": "can't get status for device with id: {id}"}, 404
    temp, speed, duty = status
    return {"temp": temp, "speed": speed, "duty": duty}, 200


@app.route("/devices/<int:id>/speed", methods=["POST"])
def set_speed(id: int):
    if not request.method == "POST":
        return {"status": "Method not allowed"}, 405
    data = request.get_json()
    if "channel" not in data or "profile" not in data:
        return {"error": "missing required parameter"}, 404
    channel: str = data.get("channel")
    profile: List = data.get("profile")
    print(profile)
    if not kraken_service.set_speed_profile(id, channel, profile):
        return {"error": "no device found"}, 404
    return {"status": "OK"}, 200


@app.route("/devices/<int:id>/color", methods=["POST"])
def set_color(
    id: int,
):
    if not request.method == "POST":
        return {"status": "Method not allowed"}, 405

    data = request.get_json()
    channel = data.get("channel")
    mode = data.get("mode")
    colors = data.get("colors")
    speed = data.get("speed")
    direction = data.get("direction")

    if not channel or not mode or not colors or not speed or not direction:
        return {"status": "missing requiered field"}, 404

    kraken_service.set_device_color(id, channel, mode, colors, speed, direction)
    return {"status": "OK"}, 200


if __name__ == "__main__":
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=8080)
    app.run(debug=True)
