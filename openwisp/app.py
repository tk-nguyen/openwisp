from flask import Flask, jsonify, render_template, request, redirect
from flask.helpers import url_for
from openwisp.utils import (
    get_conntrack,
    get_device,
    get_device_group,
    get_metrics,
    get_template,
    create_device,
    create_template,
)
from openwisp.forms import CreateDeviceForm
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


@app.route("/devices")
def list_devices():
    devices = get_device()
    return render_template("list_devices.html", devices=devices)


@app.route("/devices/create", methods=["GET", "POST"])
def create_new_device():
    form = CreateDeviceForm()
    if request.method == "POST":
        if form.validate_on_submit():
            result = create_device(form)
            return redirect(url_for("list_devices"))
    return render_template("create_device.html", form=form)


@app.route("/devices/<int:id>")
def metrics(id):
    metrics = get_metrics(id - 1)
    conntrack = get_conntrack()
    return render_template("metrics.html", metrics=metrics, conntrack=conntrack)


@app.route("/templates")
def list_templates():
    templates = get_template()
    return render_template("list_templates.html", templates=templates)
