import argparse
import sqlite3
import threading
import time

import flask
from flask import Flask, request, g
import os
import os.path
import sys
import json
import datetime
from typing import List

from cartograph.photodata import PhotodataThread
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

os.makedirs(os.path.dirname(app.config["DB_LOCATION"]), exist_ok=True)

photodata_thread = PhotodataThread(webdav_url=app.config["WEBDAV_URL"],
                                   webdav_login=app.config["WEBDAV_LOGIN"],
                                   webdav_password=app.config["WEBDAV_PASSWORD"],
                                   minutes=15,
                                   db_path=app.config["DB_LOCATION"],
                                   remote_path=app.config["WEBDAV_FILE_PATH"],
                                   local_path=app.config["PHOTO_LOCATION"])
photodata_thread.start()

geodata = GeodataClient(app.config["GEODATA_MAIL_HOST"],
                        app.config["GEODATA_MAIL_USER"],
                        app.config["GEODATA_MAIL_PASSWORD"])
geodata_thread = GeodataThread(geodata, 15, app.config["DB_LOCATION"])
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
    print("[cartograph] request for /")
    print("[cartograph] extracting waypoints")
    waypoints = extract_waypoints()
    print("[cartograph] collating photos")
    collation = collate_photos(waypoints)
    print("[cartograph] begin render template")
    return flask.render_template('index.jinja2', waypoints=waypoints, collation=collation)


def extract_waypoints() -> List[DatedLatLng]:
    con = sqlite3.connect(app.config["DB_LOCATION"])
    cur = con.execute("SELECT * FROM Geodata ORDER BY date")
    points = cur.fetchall()
    con.close()
    waypoints = []
    for point in points:
        waypoints.append(DatedLatLng(datetime.datetime.fromtimestamp(int(point[0])), point[1], point[2]))
    return waypoints


def path_pos_from_latlng(waypoints: List[DatedLatLng], pos: DatedLatLng) -> (int, float):
    if len(waypoints) <= 1:
        return (0, 0.001)

    closest_ix = min(range(len(waypoints)), key=lambda i:waypoints[i].sqdist(pos))
    closest_dist = waypoints[closest_ix].dist(pos)

    next_closest_ix = 0
    if closest_ix == 0:
        next_closest_ix = 1
    elif closest_ix == len(waypoints) - 1:
        next_closest_ix = len(waypoints) - 2
    elif waypoints[closest_ix - 1].sqdist(pos) > waypoints[closest_ix + 1].sqdist(pos):
        next_closest_ix = closest_ix + 1

    next_closest_dist = waypoints[next_closest_ix].dist(pos)
    fract_on_segment = closest_dist / (closest_dist + next_closest_dist)

    fract_on_segment = int(fract_on_segment * 10) / 10

    if next_closest_ix > closest_ix:
        return (closest_ix, fract_on_segment + 0.001)
    else:
        return (next_closest_ix, 1 - fract_on_segment - 0.001)


class CollationPoint:
    def __init__(self, pos: DatedLatLng, main_idx: int, sub_idx: float):
        self.pos = pos
        self.main_idx = main_idx
        self.sub_idx = sub_idx
        self.photos = []

def collate_photos(waypoints: List[DatedLatLng]) -> List[List[CollationPoint]]:
    con = sqlite3.connect(app.config["DB_LOCATION"])
    cur = con.execute("SELECT * FROM Photodata")
    data = cur.fetchall()
    con.close()

    start = time.time()
    collation = [[] for _ in waypoints]

    for (filename, date, lat, lng) in data:
        latlng = DatedLatLng(datetime.datetime.fromtimestamp(int(date)), lat, lng)
        main_idx, sub_idx = path_pos_from_latlng(waypoints, latlng)

        if not collation[main_idx]:
            new_cpoint = CollationPoint(latlng, main_idx, sub_idx)
            new_cpoint.photos.append(filename)
            collation[main_idx].append(new_cpoint)
            continue


        for i, collation_point in enumerate(collation[main_idx]):
            if collation_point.sub_idx >= sub_idx:
                break

        if collation_point.sub_idx == sub_idx:
            collation_point.photos.append(filename)
        elif collation_point.sub_idx > sub_idx:
            new_cpoint = CollationPoint(latlng, main_idx, sub_idx)
            new_cpoint.photos.append(filename)
            collation[main_idx].insert(i, new_cpoint)
        else:
            new_cpoint = CollationPoint(latlng, main_idx, sub_idx)
            new_cpoint.photos.append(filename)
            collation[main_idx].append(new_cpoint)

    end = time.time()
    print(f"[cartograph] Collation took {end - start:.1f} seconds")
    return collation


if "SITE_NAME" not in app.config:
    app.config["SITE_NAME"] = "Cartograph"
