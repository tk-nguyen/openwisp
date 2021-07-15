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


# def get_token():
#    try:
#        password = os.environ["PASS"]
#        auth_data = {"username": "admin", "password": password}
#        res = ses.post(f"{URI}/user/token/", data=auth_data).json()
#        token = res.get("token")
#    except KeyError:
#        logger.error("Please set the PASS environment variable!")
#    except Exception as e:
#        logger.error(f"There seems to be an error: {e}")


def get_device():
    try:
        res = ses.get(f"{URI}/controller/device").json()
        devices = res.get("results")
        return devices
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")
