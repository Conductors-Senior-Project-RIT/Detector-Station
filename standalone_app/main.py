import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "EOT"))
from EOT import information_sender, decoders

from PyQt6 import QtWidgets

from QtGUI.TrackSenseGUIWrapper import TrackSenseGUIWrapper


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = TrackSenseGUIWrapper()
    window.show()
    sys.exit(app.exec())
