from flask import Flask, jsonify, render_template, request, flash, redirect
from flask.helpers import url_for
from openwisp.utils import *
from dotenv import load_dotenv

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
    return render_template("list_device.html", devices=devices)


@app.route("/devices/create", methods=["GET", "POST"])
def create_new_device():
    if request.method == "GET":
        return render_template("create_device.html")
    if request.method == "POST":
        data = request.form
        result = create_device(data)
        flash(result)
        return redirect(url_for("list_devices"))


@app.route("/devices/<int:id>")
def metrics(id):
    metrics = get_metrics(id - 1)
    return render_template("metrics.html", metrics=metrics)


@app.route("/templates")
def templates():
    return jsonify(get_template())
