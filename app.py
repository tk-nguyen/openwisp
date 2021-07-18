from flask import Flask, jsonify, render_template
from openwisp.utils import *
from dotenv import load_dotenv

load_dotenv()
app = Flask("openwisp")


@app.route("/")
def main_page():
    return render_template("index.html")


@app.route("/device-group")
def device_group():
    return jsonify(get_device_group())


@app.route("/devices")
def devices():
    devices = get_device()
    return render_template("device.html", devices=devices)


@app.route("/templates")
def templates():
    return jsonify(get_template())
