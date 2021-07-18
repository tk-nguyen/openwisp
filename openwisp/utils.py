import os
import logging
from requests.sessions import Session


logging.captureWarnings(True)
logger = logging.getLogger(__name__)
logger.info("Starting the openwisp watcher...")

URI = "https://172.20.20.10/api/v1"
ses = Session()
ses.verify = False
try:
    ses.headers.update({"Authorization": f"Bearer {os.environ['TOKEN']}"})
    ses.headers.update({"Accept": "application/json"})
except Exception as e:
    logger.error(f"There seems to be an error: {e}")

"""
Get the list of OpenWRT devices currently registered to this OpenWISP controller
"""


def get_device():
    try:
        res = ses.get(f"{URI}/controller/device").json()
        devices = res.get("results")
        return devices
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


"""
Get the device groups, which contains OpenWRT devices
"""


def get_device_group():
    try:
        res = ses.get(f"{URI}/controller/groups").json()
        device_group = res.get("results")
        return device_group
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


"""
Get the list of templates (configurations settings) for OpenWRT devices
"""


def get_template():
    try:
        res = ses.get(f"{URI}/controller/template").json()
        templates = res.get("results")
        return templates
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")
