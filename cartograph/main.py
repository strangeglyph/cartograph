import argparse
import sqlite3
import threading

import flask
from flask import Flask, request, g
import os
import os.path
import sys
import json
import datetime
from cartograph.geodata import GeodataThread, GeodataClient
from cartograph.latlng import DatedLatLng



# Hack for executing from different root dirs
def get_data_path(relpath: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relpath)


app = Flask(__name__, template_folder=get_data_path("Templates"))
if os.getenv("CARTOGRAPH_CONFIG"):
    print(f"Loading config from {os.getenv('CARTOGRAPH_CONFIG')}")
    app.config.from_file(os.getenv("CARTOGRAPH_CONFIG"), load=json.load)
app.config.from_prefixed_env()


def adapt_datetime_epoch(val):
    """Adapt datetime.datetime to Unix timestamp."""
    return int(val.timestamp())


def convert_timestamp(val):
    """Convert Unix epoch timestamp to datetime.datetime object."""
    return datetime.datetime.fromtimestamp(int(val))


sqlite3.register_adapter(datetime.datetime, adapt_datetime_epoch)
sqlite3.register_converter("timestamp", convert_timestamp)

geodata = GeodataClient(app.config["GEODATA_MAIL_HOST"],
                        app.config["GEODATA_MAIL_USER"],
                        app.config["GEODATA_MAIL_PASSWORD"])
geodata_thread = GeodataThread(geodata, 1, app.config["DB_LOCATION"])
geodata_thread.start()


@app.context_processor
def inject_site_info():
    root = app.config["APPLICATION_ROOT"]
    if root == "/":
        # Double slashes on the first segment of a domain-relative URL turns it into a protocol-relative URL
        # (i.e. the first segment is expected to be a domain name, not the first path segment),
        # so we turn the default application root of "/" into an empty string for our templates
        root = ""
    return dict(site_name=app.config["SITE_NAME"], base_url=app.config["BASE_URL"], root=root)


@app.route("/")
def index():
    con = sqlite3.connect(app.config["DB_LOCATION"])
    cur = con.execute("SELECT * FROM Geodata ORDER BY date")
    points = cur.fetchall()
    print(points)
    con.close()
    waypoints = []
    for point in points:
        waypoints.append(DatedLatLng(datetime.datetime.fromtimestamp(int(point[0])), point[1], point[2]))
    return flask.render_template('index.jinja2', waypoints=waypoints)


if "SITE_NAME" not in app.config:
    app.config["SITE_NAME"] = "Cartograph"
