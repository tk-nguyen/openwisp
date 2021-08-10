import os
import logging
import json
import time
import redis
from openwisp.connection import Connection
from requests.sessions import Session

logging.captureWarnings(True)
logger = logging.getLogger(__name__)
logger.info("Starting the openwisp watcher...")


# Set up the connection to the OpenWISP REST endpoint
OPENWISP_URI = "https://172.20.20.10/api/v1"
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
        res = openwisp.get(f"{OPENWISP_URI}/controller/device/")
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
            f"{OPENWISP_URI}/controller/device/",
            json=form.data,
        )
        res.raise_for_status()
        return "Device created successfully!"
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")
        return "Cannot create the device"


def get_device_group():
    try:
        res = openwisp.get(f"{OPENWISP_URI}/controller/groups/")
        res.raise_for_status()
        device_group = res.json().get("results")
        return device_group
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def get_template():
    try:
        res = openwisp.get(f"{OPENWISP_URI}/controller/template/")
        res.raise_for_status()
        templates = res.json().get("results")
        return templates
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def create_template(form):
    try:
        res = openwisp.post(f"{OPENWISP_URI}/controller/template/")
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
            f"{OPENWISP_URI}/monitoring/device/{device_id}/",
            params={"key": device_key, "status": "true"},
        )
        res.raise_for_status()
        metrics = res.json().get("data")
        return metrics
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


# Track the endpoint through this machine
def track_connections():
    try:
        result = luci_rpc.get(f"{LUCI_URI}/sys", json={"method": "net.conntrack"})
        result.raise_for_status()
        conntrack = result.json().get("result")
        tracked = []
        # We're gonna track each connection returned from the call
        for cnt in conntrack:
            if len(tracked) == 0 and cnt["layer3"] == "ipv4":
                origin = Connection(cnt["src"])
                origin.add_conn(cnt["dst"], cnt["dport"], cnt["bytes"])
                tracked.append(origin)
            elif cnt["layer3"] == "ipv4":
                found = False
                for trck in tracked:
                    if trck.src == cnt["src"]:
                        found = True
                        trck.add_conn(cnt["dst"], cnt["dport"], cnt["bytes"])
                        break
                if not found:
                    origin = Connection(cnt["src"])
                    origin.add_conn(cnt["dst"], cnt["dport"], cnt["bytes"])
                    tracked.append(origin)
        return tracked
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def run_command(command):
    try:
        # Run the command by POSTing
        payload = {"input": {"command": f"{command}"}, "type": "custom"}
        result = openwisp.post(
            f"{OPENWISP_URI}/controller/device/5fb06af2-3ada-41b6-bb13-52d46ef3a9ee/command/",
            json=payload,
        )
        result.raise_for_status()
        # Get the command result
        command_id = result.json().get("id")
        success = False
        while not success:
            output = openwisp.get(
                f"{OPENWISP_URI}/controller/device/5fb06af2-3ada-41b6-bb13-52d46ef3a9ee/command/{command_id}/"
            )
            output.raise_for_status()
            status = output.json().get("status")
            if status == "success":
                success = True
                return output.json().get("output")
            elif status == "in-progress":
                time.sleep(2)
            elif status == "failed":
                return output.json().get("output")
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def traffic_control():
    data = track_connections()
    interface = "br-lan"
    counter = 1
    # First we setup basic stuff:
    if data is None:
        return "Error"

    run_command(f"tc qdisc add dev {interface} root handle 1: htb default 1")
    limited = {}
    for conn in data:
        for endpoint, bytes in conn.conns.items():
            # Check if class is already created
            # add the bandwidth limit if it isn't
            # else change the bandwidth limit
            if endpoint[0] not in limited:
                if bytes > 100:
                    run_command(
                        f"tc class add dev {interface} parent 1: classid 1:{counter} htb rate {100000/bytes}kbps"
                    )
                    run_command(
                        f"tc filter add dev {interface} protocol ip parent 1: prio 0 u32 match ip dst {endpoint[0]}/32 flowid 1:{counter}"
                    )
                    limited[endpoint[0]] = f"1:{counter}"
                    counter += 1
            else:
                if bytes > 100:
                    run_command(
                        f"tc class change dev {interface} parent 1: classid {limited[endpoint[0]]} htb rate {100000/bytes}kbps"
                    )
                    run_command(
                        f"tc filter change dev {interface} protocol ip parent 1: prio 0 u32 match ip dst {endpoint[0]}/32 flowid {limited[endpoint[0]]}"
                    )

    result = []
    result.append(run_command(f"tc -s -d -p qdisc show dev {interface}"))
    result.append(run_command(f"tc -s -d -p class show dev {interface}"))
    result.append(run_command(f"tc -s -d -p filter show dev {interface}"))
    return result


def reset_traffic_control():
    interface = "br-lan"
    output = run_command(f"tc qdisc show dev {interface} root")
    if output == "":
        run_command(f"tc qdisc del dev {interface} root")
        return "Success"
    else:
        return "There is no traffic control"
