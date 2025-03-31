import argparse

import flask
from flask import Flask, request, g
import os
import os.path
import sys
import json

# Hack for executing from different root dirs
def get_data_path(relpath: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relpath)


app = Flask(__name__, template_folder=get_data_path("Templates"))
if os.getenv("CARTOGRAPH_CONFIG"):
    print(f"Loading config from {os.getenv('CARTOGRAPH_CONFIG')}")
    app.config.from_file(os.getenv("CARTOGRAPH_CONFIG"), load=json.load)
app.config.from_prefixed_env()


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
    return flask.render_template('index.jinja2')


if "SITE_NAME" not in app.config:
    app.config["SITE_NAME"] = "Cartograph"
