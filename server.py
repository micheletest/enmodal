# Flask and plugins
from flask import Flask, render_template, request, after_this_request
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)

# enmodal libraries
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from EnmodalCore import enmodal
from EnmodalMap import enmodal_map
from EnmodalSessions import *
from EnmodalGTFS import enmodal_gtfs

# psycopg2
import psycopg2
import psycopg2.extras

# misc
import uuid
import json

# config
import configparser

config = configparser.RawConfigParser()
config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), "settings.cfg")))


def get_conf(section, option):
    val = os.environ.get(f"{section.upper()}_{option.upper()}")
    if val is not None:
        return val
    return config.get(section, option)


PORT_HTTP = int(get_conf("flask", "port_http"))
SESSIONS_HOST = get_conf("sessions", "host")
SESSIONS_PORT = get_conf("sessions", "port")
SESSIONS_DBNAME = get_conf("sessions", "dbname")
SESSIONS_USER = get_conf("sessions", "user")
SESSIONS_PASSWORD = get_conf("sessions", "password")
SESSIONS_CONN_STRING = (
    "host='"
    + SESSIONS_HOST
    + "' port='"
    + SESSIONS_PORT
    + "' dbname='"
    + SESSIONS_DBNAME
    + "' user='"
    + SESSIONS_USER
    + "' password='"
    + SESSIONS_PASSWORD
    + "'"
)
SESSIONS_SECRET_KEY_PUBLIC = int(get_conf("sessions", "secret_key_public"), 16)
SESSIONS_SECRET_KEY_PRIVATE = int(get_conf("sessions", "secret_key_private"), 16)
SESSION_EXPIRATION_TIME = int(get_conf("sessions", "expiration_time"))
UPLOAD_FOLDER = get_conf("flask", "upload_folder")
SCREENSHOT_FOLDER = get_conf("flask", "screenshot_folder")

# set up app object
application = Flask(
    __name__, static_folder="dist", template_folder="dist", static_url_path="/static"
)
application.register_blueprint(enmodal)
application.secret_key = get_conf("flask", "secret_key")

login_manager = LoginManager()
login_manager.init_app(application)

application.register_blueprint(enmodal_map)
application.register_blueprint(enmodal_gtfs)


@login_manager.user_loader
def load_user(user):
    return User.get(user)


@application.route("/health")
def route_health():
    try:
        conn = psycopg2.connect(SESSIONS_CONN_STRING)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return json.dumps({"status": "ok", "db": "connected"})
    except Exception as e:
        return json.dumps({"status": "error", "db": str(e)}), 500


@application.route("/session")
def route_session_status():
    s = EnmodalSession()
    session_manager.add(s)
    a = session_manager.auth_by_key(s.private_key())

    return_obj = {
        "is_private": a.editable,
        "public_key": "{:16x}".format(a.session.public_key()),
    }

    if not a.editable:
        print(
            f"WARNING: Session created but not editable. DB persistence might be failing. Public key: {a.session.public_key():x}"
        )

    if a.editable:
        return_obj["private_key"] = "{:16x}".format(a.session.private_key())
    del a
    return json.dumps(return_obj)


def run_server():
    application.run(host="0.0.0.0", port=PORT_HTTP)


if __name__ == "__main__":

    if not os.path.isdir(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    if not os.path.isdir(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)

    run_server()
