import pyaudio
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from TrackSenseLogger import logger


class AudioComponent(QObject):
    db_min = 0
    db_max = 90
    audioRead = pyqtSignal(int)

    def __init__(self, aud_devc):
        super().__init__()
        self.db = 0
        self.aud_devc = aud_devc
        self.go = True

    @pyqtSlot(str)
    def setAudioDevice(self, aud_devc):
        self.aud_devc = aud_devc
        self.db_max = 90

    @pyqtSlot()
    def runVolMon(self):
            self.go = True
            # init stuff
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 2
            RATE = 44100
            p = pyaudio.PyAudio()
            input_device_idx = 0

            # set audio input
            info = p.get_host_api_info_by_index(0)
            num_devc = info.get('deviceCount')
            for i in range(0, num_devc):
                if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                    device_name = p.get_device_info_by_host_api_device_index(0, i).get('name')
                    logger.debug(f"Input device id {i} - {device_name}")
                    if device_name == self.aud_devc:
                        logger.debug(f"owo {device_name}")
                        input_device_idx = i

            # max_vol = 0
            # min_vol = 1

            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK,
                            input_device_index=input_device_idx)

            while self.go:
                data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
                rms = np.sqrt(np.mean(np.float32(data) ** 2))    # This is the code to calculate the root-mean-square
                self.db = 20 * np.log10(rms) if rms > 0 else 0

                # Update db_max if db is louder
                self.db_max = max(self.db_max, self.db)

                # Calculate percentage volume, but clamp between 0 and 100%
                pct = int((self.db-self.db_min) / (self.db_max - self.db_min) * 100)
                pct = max(0, min(pct, 100))
                self.audioRead.emit(pct)

            stream.stop_stream()
    
    def stop(self):
        self.go = False

    def getVol(self):
        return self.db

    def getMin(self):
        return self.db_min

    def getMax(self):
        return self.db_max
