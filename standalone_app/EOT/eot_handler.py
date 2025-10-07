# Rewrite of Eric Reuter's PyEOT main script to handle our use case
# Written by Jon Poret - RIT 2025, Tracksense
import zmq
import collections
import datetime
import threading
import os, sys
from PyQt6 import QtCore, QtGui, QtWidgets, QtMultimedia
from PyQt6.QtCore import pyqtSignal, QObject, pyqtSlot, QThreadPool
import copy, configparser
from information_sender import *
from TrackSenseLogger import logger
from decoders import EOTDecoder, HOTDecoder

from EOT.ping import HeartbeatPingThread

from EOT.dropped_data_handler import DroppedDataHandler


# sys.path.append(os.path.join(os.path.dirname(__file__), 'PyEOT'))


class EOTHandler(QObject):

    config = configparser.ConfigParser()
    config.read("tracksenseConfig.ini")
    host_url = config["connection"]["url"].strip()
    stat_id = config["connection"]["station_id"].strip()

    date_str = str(datetime.datetime.now().strftime("%Y %m %d"))
    EOT_FRAME_SYNC = "10101011100010010"
    HOT_FRAME_SYNC = "010101100011110001000100101001"
    DPU_FRAME_SYNC = "0011101100010110"
    context = None
    sock = None
    queue = collections.deque(maxlen=256)
    listenerThread = None
    listen = False
    combined_file = None
    eot_file = None
    hot_file = None
    eot_file_name = date_str + " eot data.txt"
    hot_file_name = date_str + " hot data.txt"
    combined_file_name = date_str + " combined data.txt"
    test = pyqtSignal(dict)
    dict_template = {
        "Timestamp": [],
        "Unit Address": [],
        "Source": [],
        "Arm Status": [],
        "Battery Condition": [],
        "Battery Charge": [],
        "Pressure": [],
        "Turbine Status": [],
        "Motion Status": [],
        "Marker Light": [],
        "Marker Battery": [],
        "HOT Command": [],
        "Signal Strength": [],
    }
    # test.connect(TrackSenseGUIWrapper.updateTable)
    onlineMode = True
    enableHeartbeat = pyqtSignal()
    disableHeartbeat = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.SUB)
        self.eot_decoder = EOTDecoder()
        self.hot_decoder = HOTDecoder()

        self.heartbeatThread = HeartbeatPingThread(self.host_url, self.stat_id)
        self.enableHeartbeat.connect(self.heartbeatThread.worker.start_timer)
        self.disableHeartbeat.connect(self.heartbeatThread.worker.stop_timer)

        self.heartbeatThread.start()

        self.dropDataHandler = DroppedDataHandler("dropped_data.json", self.host_url)

        # generate files for logging data

    def getAudioPercentage(self, audioProcessor, vol):
        dbMin = audioProcessor.getMin()
        dbMax = audioProcessor.getMax()
        pct = int((vol - dbMin) / (dbMax - dbMin) * 100)
        return max(0, min(pct, 100))

    def listenLoop(self, saveEot, saveHot, saveComb, audioProcessor):
        if saveEot:
            try:
                self.eot_file = open(self.eot_file_name, "a+")
            except FileNotFoundError:
                self.eot_file = open(self.eot_file_name, "xw+")
        if saveHot:
            try:
                self.hot_file = open(self.hot_file_name, "a+")
            except FileNotFoundError:
                self.hot_file = open(self.hot_file_name, "xw+")
        if saveComb:
            try:
                self.combined_file = open(self.combined_file_name, "a+")
            except FileNotFoundError:
                self.combined_file = open(self.combined_file_name, "xw+")
        context = zmq.Context()
        sock = context.socket(zmq.SUB)
        queue = collections.deque(maxlen=256)
        sock.connect("tcp://localhost:5555")
        sock.setsockopt(zmq.SUBSCRIBE, b"")

        poller = zmq.Poller()
        poller.register(sock, zmq.POLLIN)

        while self.listen:
            # obtain data
            socks = dict(poller.poll(1000))
            if sock in socks:
                dat = sock.recv()
                vol = audioProcessor.getVol()
                for byte in dat:
                    queue.append(str(byte))

                    buffer = ""  # clear the buffer
                    for bit in queue:
                        buffer += bit  # add bits to the buffer from the queue
                    # look for frame sync - tells us which signal we're decoding
                    if buffer.find(self.EOT_FRAME_SYNC) == 0:
                        data_to_send = buffer[6:]
                        # self.checkSignalMax(vol)
                        pct = self.getAudioPercentage(audioProcessor, vol)
                        self.handle_EOT(data_to_send, pct)
                    elif buffer.find(self.HOT_FRAME_SYNC) == 0:
                        data_to_send = buffer[6:]
                        # self.checkSignalMax(vol)
                        pct = self.getAudioPercentage(audioProcessor, vol)
                        self.handle_HOT(data_to_send, pct)
            else:
                logger.warning("Not connected to GNU radio")

    def handle_EOT(self, eot, pct):
        time_rec = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
        eot1 = self.eot_decoder.decode_eot(eot)  # should rename var but whatever
        if eot1 is not None:
            eot_str = f"""
                {time_rec} EOT DECODED:
                Unit Address: {eot1['unit_address']}
                Arm Status: {eot1['arm_status']}
                Battery Condition: {eot1['battery_condition']}
                Battery Charge: {eot1['battery_charge']}
                Pressure: {eot1['pressure']}
                Turbine Status: {eot1['turbine_status']}
                Motion: {eot1['motion_status']}
                Marker Light: {eot1['marker_light']}
                Marker Battery: {eot1['marker_battery']}
                Signal Strength: {pct}
                \n\n\n
            """
            # if self.eot_file is None:
            #     pass
            # else:
            if self.eot_file is not None:
                self.eot_file.write(eot_str)
                self.eot_file.flush()
            if self.combined_file is not None:
                self.combined_file.write(eot_str)
                self.combined_file.flush()
            logger.debug(eot_str)
            table_data = copy.deepcopy(self.dict_template)
            table_data["Timestamp"] = time_rec
            table_data["Unit Address"] = eot1["unit_address"]
            table_data["Source"] = "EOT"
            table_data["Arm Status"] = eot1["arm_status"]
            table_data["Battery Condition"] = eot1["battery_condition"]
            table_data["Battery Charge"] = eot1["battery_charge"]
            table_data["Pressure"] = eot1["pressure"]
            table_data["Turbine Status"] = eot1["turbine_status"]
            table_data["Motion Status"] = eot1["motion_status"]
            table_data["Marker Light"] = eot1["marker_light"]
            table_data["Marker Battery"] = eot1["marker_battery"]
            table_data["HOT Command"] = eot1["hot_command"]
            table_data["Signal Strength"] = pct
            self.test.emit(table_data)

            if self.onlineMode:
                worker = EOTRequestWorker(
                    eot1,
                    self.host_url,
                    self.stat_id,
                    pct,
                    time_rec,
                    self.dropDataHandler,
                )
                worker.signals.onError.connect(self.response_error_handle)
                QThreadPool.globalInstance().start(worker)

    def handle_HOT(self, hot, pct):
        time_rec = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
        hot1 = self.hot_decoder.decode_hot(hot)
        if hot1 is not None:
            hot_str = f"""
                {time_rec} HOT DECODED:
                Unit address: {hot1['unit address']}
                Command: {hot1['command']}
                Signal Strength: {pct}
                \n\n\n
            """
            logger.debug(hot_str)
            table_data = copy.deepcopy(self.dict_template)
            table_data["Timestamp"] = time_rec
            table_data["Unit Address"] = hot1["unit address"]
            table_data["Source"] = "HOT"
            table_data["Arm Status"] = None
            table_data["Battery Condition"] = None
            table_data["Battery Charge"] = None
            table_data["Pressure"] = None
            table_data["Turbine Status"] = None
            table_data["Motion Status"] = None
            table_data["Marker Light"] = None
            table_data["Marker Battery"] = None
            table_data["HOT Command"] = hot1["command"]
            table_data["Signal Strength"] = pct
            self.test.emit(table_data)
            if self.onlineMode:
                worker = HOTRequestWorker(
                    hot1,
                    self.host_url,
                    self.stat_id,
                    pct,
                    time_rec,
                    self.dropDataHandler,
                )
                worker.signals.onError.connect(self.response_error_handle)
                QThreadPool.globalInstance().start(worker)

            if self.hot_file is not None:
                self.hot_file.write(hot_str)
                self.hot_file.flush()
            if self.combined_file is not None:
                self.combined_file.write(hot_str)
                self.combined_file.flush()

    @pyqtSlot(str)
    def response_error_handle(self, msg):
        logger.error(msg)

    def startListening(self, saveEot, saveHot, saveComb, audioProcessor):
        logger.info("Tracking started.")
        if self.onlineMode:
            self.enableHeartbeat.emit()

        if self.listenerThread is None:
            self.listen = True
            self.listenerThread = threading.Thread(
                target=self.listenLoop,
                args=[saveEot, saveHot, saveComb, audioProcessor],
            )
            self.listenerThread.start()
        else:
            return -1
        return 0

    def stopListening(self):
        logger.info("Tracking stopped.")
        if self.onlineMode:
            self.disableHeartbeat.emit()

        if self.listenerThread is not None:
            self.listen = False
            self.listenerThread.join()
            self.listenerThread = None
            if self.eot_file is not None:
                self.eot_file.close()
                self.eot_file = None
            if self.hot_file is not None:
                self.hot_file.close()
                self.hot_file = None
            if self.combined_file is not None:
                self.combined_file.close()
                self.combined_file = None
        else:
            return -1
        return 0

    @pyqtSlot(int)
    def setOnlineMode(self, onlineMode):
        self.onlineMode = onlineMode
