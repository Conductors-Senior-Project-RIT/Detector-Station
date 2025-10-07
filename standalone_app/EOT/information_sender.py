import requests
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from requests import RequestException, Timeout
import json


class WorkerSignals(QObject):
    onError = pyqtSignal(str)
    savePacket = pyqtSignal(object)
    success = pyqtSignal()


class EOTRequestWorker(QRunnable):
    def __init__(self, eot_pkt, host, stat_id, pct, timestamp, dropped_data_handler):
        super().__init__()
        self.eot_pkt = eot_pkt
        self.host = host.strip('"')
        self.stat_id = stat_id
        self.pct = pct
        self.signals = WorkerSignals()
        self.timestamp = timestamp
        self.dropHandler = dropped_data_handler
        self.signals.savePacket.connect(self.dropHandler.handle_dropped_packet)
        self.signals.success.connect(self.dropHandler.send_saved_packets)

    def run(self):
        req_type = 1

        request_obj = {
            "type": req_type,
            "station_id": self.stat_id,
            "unit_addr": self.eot_pkt["unit_address"],
            "brake_pressure": self.eot_pkt["pressure"],
            "motion": self.eot_pkt["motion_status"],
            "marker_light": self.eot_pkt["marker_light"],
            "turbine": self.eot_pkt["turbine_status"],
            "battery_cond": self.eot_pkt["battery_condition"],
            "battery_charge": self.eot_pkt["battery_charge"],
            "arm_status": self.eot_pkt["arm_status"],
            "signal_strength": self.pct,
        }

        try:
            resp = requests.post(
                f"{self.host}/api/history",
                json=request_obj,
            )
            resp.raise_for_status()
            self.signals.success.emit()
        except Timeout:
            request_obj["date_rec"] = self.timestamp
            self.signals.savePacket.emit(request_obj)
            # self.dropHandler.handle_dropped_packet(request_obj)
            self.signals.onError.emit("EOT Request timed out.")

        except RequestException as re:
            request_obj["date_rec"] = self.timestamp
            self.signals.savePacket.emit(request_obj)
            # self.dropHandler.handle_dropped_packet(request_obj)
            self.signals.onError.emit(str(re))
        return


class HOTRequestWorker(QRunnable):
    def __init__(self, hot_pkt, host, stat_id, pct, timestamp, dropped_data_handler):
        super().__init__()
        self.hot_pkt = hot_pkt
        self.host = host
        self.stat_id = stat_id
        self.pct = pct
        self.signals = WorkerSignals()
        self.time_rec = timestamp
        self.dropHandler = dropped_data_handler
        self.signals.savePacket.connect(self.dropHandler.handle_dropped_packet)
        self.signals.success.connect(self.dropHandler.send_saved_packets)

    def run(self):
        req_type = 2

        request_obj = {
            "type": req_type,
            "station_id": self.stat_id,
            "unit_addr": self.hot_pkt["unit address"],
            "command": self.hot_pkt["command"],
            "signal_strength": self.pct,
        }

        try:
            resp = requests.post(
                f"{self.host}/api/history",
                json=request_obj,
            )
            resp.raise_for_status()
            self.signals.success.emit()
        except Timeout:
            request_obj["date_rec"] = self.time_rec
            self.signals.savePacket.emit(request_obj)
            # self.dropHandler.handle_dropped_packet(request_obj)
            self.signals.onError.emit("HOT Request timed out.")
        except RequestException as re:
            request_obj["date_rec"] = self.time_rec
            self.signals.savePacket.emit(request_obj)
            # self.dropHandler.handle_dropped_packet(request_obj)
            self.signals.onError.emit(str(re))
        return
