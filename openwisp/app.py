from flask import Flask, jsonify, render_template, request, redirect
from flask.helpers import url_for
from openwisp.utils import (
    get_device,
    get_device_group,
    get_metrics,
    get_template,
    create_device,
    reset_traffic_control,
    run_command,
    traffic_control,
)
from openwisp.forms import CreateDeviceForm, RunCommandForm
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]


@app.route("/")
def main_page():
    return render_template("index.html")


@app.route("/device-group")
def device_group():
    return jsonify(get_device_group())


@app.route("/devices", methods=["GET", "POST"])
def list_devices():
    devices = get_device()
    command_form = RunCommandForm()
    if request.method == "POST":
        if command_form.validate_on_submit():
            result = run_command(command_form.command.data)
            return render_template(
                "list_devices.html", executed=True, devices=devices, form=result
            )
    return render_template("list_devices.html", devices=devices, form=command_form)


@app.route("/devices/create", methods=["GET", "POST"])
def create_new_device():
    device_form = CreateDeviceForm()
    if request.method == "POST":
        if device_form.validate_on_submit():
            result = create_device(device_form)
            return redirect(url_for("list_devices"))
    return render_template("create_device.html", form=device_form)


@app.route("/devices/<int:id>")
def metrics(id):
    metrics = get_metrics(id - 1)
    commands = traffic_control()
    return render_template("metrics.html", metrics=metrics, stdout=commands, id=id)


@app.route("/device/<int:id>/reset", methods=["POST"])
def reset(id):
    message = reset_traffic_control()
    return render_template(
        "metrics.html", metrics={}, id=id, reset=True, message=message
    )


@app.route("/templates")
def list_templates():
    templates = get_template()
    return render_template("list_templates.html", templates=templates)