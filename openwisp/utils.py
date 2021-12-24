import os
import logging
import json
import time
import redis
from openwisp.connection import Connection
from requests.sessions import Session
from celery import shared_task

logging.captureWarnings(True)
logger = logging.getLogger(__name__)
logger.info("Starting the openwisp watcher...")


# Set up the connection to the OpenWISP REST endpoint
OPENWISP_URI = "https://172.20.20.10/api/v1"
openwisp = Session()
openwisp.verify = False
# auth = {
#     "username": os.environ["OPENWISP_USERNAME"],
#     "password": os.environ["OPENWISP_PASSWORD"],
# }
# token = openwisp.post(f"{OPENWISP_URI}/user/token/", json=auth).json()["token"]
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
token = luci_rpc.post(f"{LUCI_URI}/auth", json=auth).json()["result"]
luci_rpc.params.update({"auth": token})
# Redis connection
redis_client = redis.from_url(os.environ["REDIS_URL"])


def get_device():
    try:
        res = openwisp.get(f"{OPENWISP_URI}/controller/device/")
        res.raise_for_status()
        devices = res.json()["results"]
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
        device_group = res.json()["results"]
        return device_group
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def get_template():
    try:
        res = openwisp.get(f"{OPENWISP_URI}/controller/template/")
        res.raise_for_status()
        templates = res.json()["results"]
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
        device_id = devices[id]["id"]
        device_key = devices[id]["key"]
        res = openwisp.get(
            f"{OPENWISP_URI}/monitoring/device/{device_id}/",
            params={"key": device_key, "status": "true"},
        )
        res.raise_for_status()
        metrics = res.json()["data"]
        return metrics
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


# Track the endpoint through this machine
def track_connections():
    try:
        result = luci_rpc.get(f"{LUCI_URI}/sys", json={"method": "net.conntrack"})
        result.raise_for_status()
        conntrack = result.json()["result"]
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


# Run a command on the specified openwrt device
def run_command(command, id):
    try:
        # Run the command by POSTing
        payload = {"input": {"command": f"{command}"}, "type": "custom"}
        devices = json.loads(redis_client.get("devices"))
        device_id = devices[id]["id"]
        result = openwisp.post(
            f"{OPENWISP_URI}/controller/device/{device_id}/command/",
            json=payload,
        )
        result.raise_for_status()
        # Get the command result
        command_id = result.json()["id"]
        success = False
        while not success:
            output = openwisp.get(
                f"{OPENWISP_URI}/controller/device/{device_id}/command/{command_id}/"
            )
            output.raise_for_status()
            status = output.json()["status"]
            if status == "success":
                success = True
                return output.json()["output"]
            elif status == "in-progress":
                time.sleep(5)
            elif status == "failed":
                return output.json()["output"]
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


# Parse the /etc/services file for service port and protocol
def map_services(id):
    # The output is "<app>\t\t<port>/<proto>\n", so we split twice
    output = str(run_command("cat /etc/services", id)).strip().split("\n")
    svcs = {}
    for sv in output:
        tmp = sv.split()
        app = tmp[0]
        # We only care about the port,
        port = tmp[1].split("/")[0]
        if app not in svcs:
            svcs[app] = port
    return svcs


# Limit the traffic
def traffic_control(id):
    data = track_connections()
    interface = "br-lan"
    # max_speed = int(run_command("cat /sys/class/net/eth0/speed", id)) * 1000  # Kbps
    max_speed = 1000
    # limit = max_speed/20
    bandwidth_limit = 100

    # First we setup basic stuff:
    if data is None:
        return "Error"
    services = map_services(id)
    num_clients = get_clients(id)
    # Delete the root qdisc
    output = str(run_command(f"tc qdisc show dev {interface} root", id))
    if "htb" not in output:
        run_command(f"tc qdisc add dev {interface} root handle 1: htb default 1", id)
        run_command(
            f"tc class add dev {interface} parent 1: classid 1:1 htb rate {max_speed}kbit ceil {max_speed}kbit ",
            id,
        )
        limited = {}
        filters = {}
    else:
        limited = json.loads(redis_client.get("limits"))
        filters = json.loads(redis_client.get("filters"))

    priority = 1
    counter = 2
    filter_counter = 100
    for conn in data:
        for endpoint, bytes in conn.conns.items():
            if int(endpoint[1]) == services["ssh"]:
                priority = 1
            elif (
                int(endpoint[1]) == services["www"]
                or int(endpoint[1]) == services["https"]
            ):
                priority = 2
            else:
                priority = 10
            # Check if class is already created
            # add the bandwidth limit if it isn't
            # else change the bandwidth limit
            if endpoint[0] not in limited:
                if bytes > bandwidth_limit:
                    max_bandwidth = max_speed / num_clients
                    run_command(
                        f"tc class add dev {interface} parent 1:1 classid 1:{counter} htb rate {max_bandwidth}kbit ceil {max_speed}kbit",
                        id,
                    )

                    run_command(
                        f"tc filter add dev {interface} protocol ip parent 1: handle ::{filter_counter} prio {priority} u32 match ip src {endpoint[0]} match ip dst {conn.src} flowid 1:{counter}",
                        id,
                    )
                    limited[endpoint[0]] = {
                        "classid": f"1:{counter}",
                        "bandwidth": max_bandwidth,
                    }
                    filters[endpoint[0]] = {
                        "filter_handle": filter_counter,
                        "priority": priority
                    }
                    counter += 1
                    filter_counter += 1
                    if num_clients > 1:
                        num_clients -= 1
                    else:
                        break
                else:
                    if (max_speed - bytes > 0):
                        max_speed -= bytes
            else:
                if bytes > bandwidth_limit:
                    max_bandwidth = max_speed / num_clients
                    run_command(
                        f"tc class change dev {interface} parent 1:1 classid {limited[endpoint[0]]['classid']} htb rate {max_bandwidth}kbit ceil {max_speed}kbit",
                        id,
                    )
                    run_command(f"tc filter del dev {interface} handle 800::{filters[endpoint[0]]['filter_handle']} prio {filters[endpoint[0]]['priority']} u32", id)
                    run_command(
                        f"tc filter add dev {interface} protocol ip parent 1: handle 800::{filters[endpoint[0]]['filter_handle']} prio {filters[endpoint[0]]['priority']} u32 match ip src {endpoint[0]} match ip dst {conn.src} flowid {limited[endpoint[0]]['classid']}",
                        id,
                    )
                else:
                    if (max_speed - bytes > 0):
                        max_speed -= bytes

    result = []
    # Save the limits in redis
    redis_client.set("limits", json.dumps(limited))
    redis_client.set("filters", json.dumps(filters))
    result.append(run_command(f"tc -s -d -p qdisc show dev {interface}", id))
    result.append(run_command(f"tc -s -d -p -g class show dev {interface}", id))
    result.append(run_command(f"tc -s -d -p filter show dev {interface}", id))
    return result


def get_clients(id):
    try:
        payload = {"method": "net.ipv4_hints"}
        clients = luci_rpc.get(f"{LUCI_URI}/sys", json=payload).json()["result"]
        payload = {"method": "get_all", "params": ["network"]}
        # Get the gateway
        networks = luci_rpc.get(f"{LUCI_URI}/uci", json=payload).json()
        gateway = networks["result"]["lan"]["gateway"]
        # Then delete it from the list of clients
        for index, c in enumerate(clients):
            if c[0] == gateway:
                del clients[index]
                break
        return len(clients)
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")


def reset_traffic_control(id):
    interface = "br-lan"
    output = run_command(f"tc qdisc show dev {interface} root", id)
    if output != "":
        run_command(f"tc qdisc del dev {interface} root", id)
        return "Success"
    else:
        return "There is no traffic control"


@shared_task
def run_traffic_control(ids):
    results_per_id = {}
    try:
        for id in ids:
            results_per_id[id] = traffic_control(id)
        return results_per_id
    except Exception as e:
        logger.error(f"There seems to be an error: {e}")
