import os
import logging
from requests.sessions import Session
import redis
import json


logging.captureWarnings(True)
logger = logging.getLogger(__name__)
logger.info("Starting the openwisp watcher...")


# Set up the connection to the OpenWISP REST endpoint
URI = "https://172.20.20.10/api/v1"
openwisp = Session()
openwisp.verify = False
openwisp.headers.update(
    {
        "Authorization": f"Bearer {os.environ['TOKEN']}",
        "Accept": "*/*",
    }
)

# Redis connection
redis_client = redis.from_url(os.environ["REDIS_URL"])

# Get the list of OpenWRT devices currently registered to this OpenWISP controller
def get_device():
    try:
        res = openwisp.get(f"{URI}/controller/device/")
        res.raise_for_status()
        devices = res.json().get("results")
        redis_client.set("devices", json.dumps(devices))
        return devices
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


# Create a new OpenWRT device to be managed by this controller
def create_device(data):
    try:
        res = openwisp.post(
            f"{URI}/controller/device/",
            json=data,
        )
        res.raise_for_status()
        return "Device created successfully!"
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")
        return "Cannot create the device"


# Get the device groups, which contains OpenWRT devices
def get_device_group():
    try:
        res = openwisp.get(f"{URI}/controller/groups/")
        res.raise_for_status()
        device_group = res.json().get("results")
        return device_group
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


# Get the list of templates (configurations settings) for OpenWRT devices
def get_template():
    try:
        res = openwisp.get(f"{URI}/controller/template/")
        res.raise_for_status()
        templates = res.json().get("results")
        return templates
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


# Get the monitoring metrics of an OpenWRT device
def get_metrics(id):
    try:
        devices = json.loads(redis_client.get("devices"))
        device_id = devices[id].get("id")
        device_key = devices[id].get("key")
        res = openwisp.get(
            f"{URI}/monitoring/device/{device_id}/",
            params={"key": device_key, "status": "true"},
        )
        res.raise_for_status()
        metrics = res.json().get("data")
        return metrics
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")
