import json, os
from collections import deque

import requests
from PyQt6.QtCore import QObject, pyqtSlot, QThread, pyqtSignal
from requests import RequestException
from TrackSenseLogger import logger


class RecoverDataWorker(QObject):
    failedToSend = pyqtSignal(object)
    successful = pyqtSignal()

    def __init__(self, host, data):
        super().__init__()
        self.data = deque(data)
        self.host = host

    @pyqtSlot()
    def run(self):
        logger.debug("Running data recovery")
        while len(self.data) > 0:
            logger.debug("Sending packet")
            packet = self.data.popleft()
            try:
                resp = requests.post(
                    f"{self.host}/api/history",
                    json=packet
                )
                resp.raise_for_status()
            except RequestException as re:
                logger.error(str(re))
                # cringe
                self.data.appendleft(packet)
                self.failedToSend.emit(list(self.data))
                return
            except Exception as e:
                logger.error(str(e))

        self.successful.emit()


class DroppedDataHandler(QObject):
    droppedPackets = 0
    sendingData = False

    def __init__(self, file_name, host):
        super().__init__()
        if not os.path.exists(file_name):
            open(file_name, "w").close()

        self.file_name = file_name
        self.host = host
        self.thread = None
        self.worker = None

    @pyqtSlot(object)
    def handle_dropped_packet(self, packet):
        drop_data = []
        if not os.path.exists(self.file_name):
            open(self.file_name, "w").close()
        if os.path.getsize(self.file_name) != 0:
            with open(self.file_name, "r") as file:
                drop_data = json.load(file)
        with open(self.file_name, "w") as file:
            drop_data.append(packet)
            json.dump(drop_data, file)
            self.droppedPackets += 1

    @pyqtSlot()
    def send_saved_packets(self):
        logger.debug("Send saved packets if any")
        if self.droppedPackets == 0:
            return

        drop_data = []
        if not self.sendingData:
            with open(self.file_name, "r") as file:
                drop_data = json.load(file)

                self.sendingData = True

                self.thread = QThread()
                self.worker = RecoverDataWorker(self.host, drop_data)
                self.worker.moveToThread(self.thread)
                self.worker.failedToSend.connect(self.onFail)
                self.worker.successful.connect(self.onSuccess)
                self.thread.started.connect(self.worker.run)

                self.thread.start()

    @pyqtSlot(object)
    def onFail(self, remainingData):
        self.thread.quit()
        self.thread.wait()
        logger.debug("Packet send failed")
        self.droppedPackets = len(remainingData)
        with open(self.file_name, "w") as file:
            json.dump(remainingData, file)
        self.sendingData = False

    @pyqtSlot()
    def onSuccess(self):
        self.thread.quit()
        self.thread.wait()
        logger.debug("All packets should be sent")
        self.droppedPackets = 0
        self.worker.deleteLater()
        os.remove(self.file_name)
        self.worker = None
        self.sendingData = False
