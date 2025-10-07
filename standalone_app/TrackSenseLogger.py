import logging
from datetime import datetime

currentDate = datetime.now().strftime("%Y-%m-%d")

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(name)s:%(levelname)s %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(f"{currentDate} TrackSenseGUILog.txt"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("TrackSense")
logger.setLevel(logging.INFO)
