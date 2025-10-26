from PyQt6 import QtCore, QtGui, QtWidgets, QtMultimedia
from PyQt6.QtGui import QCloseEvent, QAction
from PyQt6.QtWidgets import QTableWidgetItem, QFileDialog, QMessageBox, QLabel
from PyQt6.QtCore import pyqtSlot, QObject, pyqtSignal, QThread, QSettings, QStandardPaths
from PyQt6.QtMultimedia import QAudioInput, QAudioFormat, QAudioDevice, QMediaDevices
import threading
from EOT.audio_amplitude import *

from QtGUI.TrackSenseGUI import Ui_guiEOTHOT
import sys, os

# sys.path.append("..")
# sys.path.append(os.path.join(os.path.dirname(__file__), '../PyEOT'))
from EOT.eot_handler import EOTHandler
import datetime

from TrackSenseLogger import logger


class TrackSenseGUIWrapper(QtWidgets.QMainWindow):
    TABLE_TEMPLATE = {
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
    date = str(datetime.datetime.now().strftime("%Y-%m-%d"))
    log_file_name = f"{date} LOG.txt"

    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_guiEOTHOT()
        self.ui.setupUi(self)
        self.ui.btnTrack.clicked.connect(self.toggleTracking)
        self.devices = QtMultimedia.QMediaDevices.audioInputs()
        for device in self.devices:
            dev_name = device.description()
            self.ui.cmboAudioSelector.addItem(dev_name)
        self.isTracking = False
        self.tracker = EOTHandler()
        self.tracker.test.connect(self.updateTable)

        self.tableActions: list[QAction] = [
            self.ui.actionTimestamp,
            self.ui.actionUnit_Address,
            self.ui.actionSource,
            self.ui.actionBattery_Condition,
            self.ui.actionBattery_Charge,
            self.ui.actionPressure,
            self.ui.actionTurbine_Status,
            self.ui.actionMotion_Status,
            self.ui.actionMarker_Light,
            self.ui.actionMarker_Battery,
            self.ui.actionHOT_Command,
            self.ui.actionSignal_Strength
        ]

        qtConfigPath = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        qtConfigFile = os.path.join(qtConfigPath, "TrackSenseGUIconfig.ini")
        self.settings = QSettings(qtConfigFile, QSettings.Format.IniFormat)

        self.ui.tblTrainData.setColumnCount(len(self.TABLE_TEMPLATE.keys()))
        self.ui.tblTrainData.setHorizontalHeaderLabels(self.TABLE_TEMPLATE.keys())

        self.ui.checkOnline.stateChanged.connect(self.tracker.setOnlineMode)

        for action in self.tableActions:
            action.changed.connect(self.changeTableVisibility)
            actionText = action.text()
            keyname = f"columns/{actionText}"
            if self.settings.contains(keyname):
                logger.debug(str(self.settings.value(keyname) == "true"))
                action.setChecked(self.settings.value(keyname) == "true")
            else:
                self.settings.setValue(keyname, True)

        self.ui.cmboAudioSelector.activated.connect(self.updateAudioDevice)

        # doing this for now cause its not connected to anything
        # self.ui.cmboAudioSelector.setEnabled(False)

        self.ui.btnLoadLog.clicked.connect(self.loadLogFile)

        # audio volume stuff
        self.audioComp = AudioComponent(self.ui.cmboAudioSelector.currentText())
        self.audioThread = QThread()
        self.audioThread.started.connect(self.audioComp.runVolMon)
        self.audioThread.finished.connect(self.restartAudioDevice)
        self.audioComp.audioRead.connect(self.ui.slidrAudioVolume.setValue)
        self.audioComp.moveToThread(self.audioThread)
        self.audioThread.start()

        # automatically assume saved to combined file
        self.ui.checkComb.setChecked(True)

    # starts tracking
    def toggleTracking(self):
        if not self.isTracking:
            # check to see what we're saving in a file
            saveToEOT = self.ui.checkEOT.isChecked()
            saveToHOT = self.ui.checkHOT.isChecked()
            saveToCombined = self.ui.checkComb.isChecked()
            logger.debug(f"{saveToEOT} {saveToHOT} {saveToCombined}")
            res = self.tracker.startListening(
                saveToEOT, saveToHOT, saveToCombined, self.audioComp
            )
            self.isTracking = res == 0
            if self.isTracking:
                self.ui.btnTrack.setText("Stop Tracking")
                self.ui.cmboAudioSelector.setEnabled(False)
                self.ui.checkOnline.setEnabled(False)
            return
        else:
            res = self.tracker.stopListening()
            self.isTracking = not (res == 0)
            if not self.isTracking:
                self.ui.btnTrack.setText("Start Tracking")
                self.ui.cmboAudioSelector.setEnabled(True)
                self.ui.checkOnline.setEnabled(True)
            return

    # updates the table with EOT data
    @pyqtSlot(dict)
    def updateTable(self, data, write_to_file=True):
        # data is a dict
        if write_to_file:
            try:
                log_file = open(self.log_file_name, "a+")
            except FileNotFoundError:
                log_file = open(self.log_file_name, "xw+")
            for key in data.keys():
                self.TABLE_TEMPLATE[key].insert(0, data[key])
                log_file.write(f"{key};{data[key]}\n")
            log_file.close()

        self.ui.tblTrainData.insertRow(0)
        for col, key in enumerate(data.keys()):
            if data[key] is not None:
                logger.debug(f"{key}: {data[key]}")
                itm = QTableWidgetItem(str(data[key]))
                self.ui.tblTrainData.setItem(0, col, itm)
        return

    # input a log file
    def loadLogFile(self):
        file_name = QFileDialog.getOpenFileName(
            self, "Open Log", "${HOME}", "Text File (*.txt)"
        )[0]
        if file_name == "":
            return
        new_data = {}
        with open(file_name, "r") as file:
            for line in file:
                dat = line.split(";")
                # key is idx 0, val is idx 1, assuming file is formatted properly
                if len(dat) == 2:
                    key = dat[0]
                    val = dat[1]
                    if key not in self.TABLE_TEMPLATE.keys():
                        self.importError()
                        return
                    else:
                        # data is properly formatted here
                        if new_data.get(key, None) is not None:
                            new_data[key].append(val)
                        else:
                            new_data[key] = [val]
                else:
                    self.importError()
                    return
        updat_dict = {}
        for i in range(len(new_data["Timestamp"])):
            updat_dict = {}
            for key in new_data.keys():
                updat_dict[key] = new_data[key][i]
        self.updateTable(updat_dict, False)
        return

    # show an import error when importing the log breaks something
    def importError(self):
        error_dialog = QMessageBox(self)
        error_dialog.setWindowTitle("ERROR")
        msg = "Improperly formatted data, unable to import"
        error_dialog.setText(msg)
        error_dialog.show()

    # hides/shows columns in the table based on whether or not its clicked
    def changeTableVisibility(self):
        col_name = self.sender().text()
        col_idx = list(self.TABLE_TEMPLATE.keys()).index(col_name)
        self.settings.setValue(f"columns/{col_name}", self.sender().isChecked())
        if self.sender().isChecked():
            self.ui.tblTrainData.showColumn(col_idx)
        elif not self.sender().isChecked():
            self.ui.tblTrainData.hideColumn(col_idx)

    # updates the audio device being used for audio monitoring
    def updateAudioDevice(self):
        new_device_name = self.ui.cmboAudioSelector.currentText()
        self.audioComp.stop()
        self.audioThread.quit()
        self.audioComp.setAudioDevice(new_device_name)

    def restartAudioDevice(self):
        self.audioThread.start()

    def closeEvent(self, event: QCloseEvent):
        self.audioThread.finished.disconnect(self.restartAudioDevice)
        self.audioComp.stop()
        self.audioThread.quit()
        self.audioThread.wait()
        self.tracker.heartbeatThread.stop()
        event.accept()
