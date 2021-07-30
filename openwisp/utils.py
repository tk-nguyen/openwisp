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

luci_rpc = Session()
LUCI_URI = "http://172.20.20.20/cgi-bin/luci/rpc"
# Auth against the luci RPC to get the token
auth = {"id": 1, "method": "login", "params": ["root", "test"]}
token = luci_rpc.post(f"{LUCI_URI}/auth", json=auth).json().get("result")
luci_rpc.params.update({"auth": token})
# Redis connection
redis_client = redis.from_url(os.environ["REDIS_URL"])


def get_device():
    try:
        res = openwisp.get(f"{URI}/controller/device/")
        res.raise_for_status()
        devices = res.json().get("results")
        # Save the devices details to redis for other endpoints
        redis_client.set("devices", json.dumps(devices))
        return devices
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def create_device(form):
    try:
        res = openwisp.post(
            f"{URI}/controller/device/",
            json=form.data,
        )
        res.raise_for_status()
        return "Device created successfully!"
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")
        return "Cannot create the device"


def get_device_group():
    try:
        res = openwisp.get(f"{URI}/controller/groups/")
        res.raise_for_status()
        device_group = res.json().get("results")
        return device_group
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def get_template():
    try:
        res = openwisp.get(f"{URI}/controller/template/")
        res.raise_for_status()
        templates = res.json().get("results")
        return templates
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def create_template(form):
    try:
        res = openwisp.post(f"{URI}/controller/template/")
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


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


def get_conntrack():
    result = (
        luci_rpc.get(f"{LUCI_URI}/sys", json={"method": "net.conntrack"})
        .json()
        .get("result")
    )
    conntrack = [data for data in result if data["src"] == "172.20.20.20"]
    return conntrack
