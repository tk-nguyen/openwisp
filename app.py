from flask import Flask, jsonify
from openwisp.utils import get_device
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)


@app.route("/")
def devices():
    return jsonify(get_device())
