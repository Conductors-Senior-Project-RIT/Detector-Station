import requests
from PyQt6.QtCore import QObject, QThread, pyqtSlot, QTimer, pyqtSignal

from TrackSenseLogger import logger
from requests import RequestException

TIMER_LENGTH_MINS = 3
MINS_TO_MS = 60000


class HeartbeatPingWorker(QObject):
    def __init__(self, url, stat_id):
        super().__init__()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.ping_server)
        self.url = url
        self.stat_id = stat_id

    @pyqtSlot()
    def ping_server(self):
        logger.debug(f"Pinging server at {self.url}/api/station_online with id {self.stat_id}")
        try:
            resp = requests.post(
                f"{self.url}/api/station_online",
                json={
                    "station_id": self.stat_id
                },
            )
            resp.raise_for_status()
        except RequestException:
            # We don't need to do anything if the request doesn't go through
            logger.debug("Couldn't ping server")
        except Exception as e:
            # Log any other exceptions
            logger.error(str(e))

    @pyqtSlot()
    def start_timer(self):
        if not self.timer.isActive():
            self.timer.start(TIMER_LENGTH_MINS * MINS_TO_MS)

    @pyqtSlot()
    def stop_timer(self):
        if self.timer.isActive():
            self.timer.stop()


class HeartbeatPingThread(QThread):
    stop_timer = pyqtSignal()

    def __init__(self, url, stat_id):
        super().__init__()
        self.worker = HeartbeatPingWorker(url, stat_id)
        self.worker.moveToThread(self)
        self.stop_timer.connect(self.worker.stop_timer)

    def run(self):
        self.exec()

    def stop(self):
        self.stop_timer.emit()
        self.quit()
        self.wait()

