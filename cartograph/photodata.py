import os
import pathlib
import sqlite3
import time
from threading import Thread
from time import sleep
import datetime

from PIL import Image, ExifTags
from regex import regex
from webdav3.client import Client

from cartograph.latlng import DatedLatLng

GPS_KEY = 34853
GPS_LAT_REF = 1
GPS_LNG_REF = 3
GPS_LAT_DATA = 2
GPS_LNG_DATA = 4
DATETIME_KEY = 306


def extract_geodata(img: Image, fallback_waypoints):
    exif = img.getexif()

    timestamp = None
    try:
        date_str = exif[DATETIME_KEY]
        timestamp = datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except KeyError:
        stem = pathlib.Path(img.filename).stem
        date_str = None
        if regex.match(r"\d{8}-\d{6}", stem):
            date_str = stem
        elif regex.match(r"IMG-\d{8}-WA\d+", stem):
            date_str = stem.split("-")[1]
        else:
            raise Exception(f"Unable to extract date info from file name: {stem}")

        timestamp = datetime.datetime.strptime(date_str, '%Y%m%d_%H%M%S')


    lat_ddeg = 0.0
    lng_ddeg = 0.0

    try:
        gps_info = exif.get_ifd(GPS_KEY)
        lat_deg, lat_min, lat_sec = gps_info[GPS_LAT_DATA]
        lat_ddeg = float(lat_deg) + float(lat_min / 60) + float(lat_sec / 3600)
        if gps_info[GPS_LAT_REF] == "S":
            lat_ddeg = -lat_ddeg

        lng_deg, lng_min, lng_sec = gps_info[GPS_LNG_DATA]
        lng_ddeg = float(lng_deg) + float(lng_min / 60) + float(lng_sec / 3600)
        if gps_info[GPS_LNG_REF] == "W":
            lng_ddeg = -lng_ddeg
    except KeyError:
        # best-effort interpolation
        waypoint_before = None
        waypoint_after = None
        for waypoint in fallback_waypoints:
            waypoint_before = waypoint_after
            waypoint_after = waypoint
            if waypoint.date >= timestamp:
                break
        lat_ddeg = (waypoint_before.latitude + waypoint_after.latitude) / 2
        lng_ddeg = (waypoint_before.longitude + waypoint_after.longitude) / 2

    return DatedLatLng(timestamp, lat_ddeg, lng_ddeg)


class PhotodataThread(Thread):
    def __init__(self, webdav_url: str, webdav_login: str, webdav_password: str, minutes: float, db_path: str,
                 remote_path: str, local_path: str):
        super().__init__()
        self.webdav_opts = {
            "webdav_hostname": webdav_url,
            "webdav_login": webdav_login,
            "webdav_password": webdav_password
        }
        self.client = Client(self.webdav_opts)
        self.minutes = minutes
        self.db_path = db_path
        self.remote_path = remote_path
        self.local_path = local_path
        con = sqlite3.connect(db_path)
        con.execute("CREATE TABLE IF NOT EXISTS Photodata(filename PRIMARY KEY, date, latitude, longitude)")
        con.commit()
        con.close()

        os.makedirs(local_path, exist_ok=True)

    def run(self):
        while True:
            self.update_photodata()
            sleep(self.minutes * 60)

    def update_photodata(self):
        sync_start = time.time()
        print("Beginning photo sync")
        try:
            updated = self.client.pull(remote_directory=self.remote_path, local_directory=self.local_path)
        except Exception as e:
            print(f"[cartograph:photo] Error: Failed to sync - {e}")
        sync_end = time.time()
        print(f"Synced files in {sync_end - sync_start:.1f} seconds")

        update_start = time.time()
        fallback_waypoints = []
        con = sqlite3.connect(self.db_path)
        cur = con.execute("SELECT * FROM Geodata ORDER BY date")
        for (date, lat, lng) in cur.fetchall():
            fallback_waypoints.append(DatedLatLng(datetime.datetime.fromtimestamp(int(date)), lat, lng))

        extracted_data = []
        for file in os.listdir(self.local_path):
            path = os.path.join(self.local_path, file)
            if os.path.isfile(path):
                try:
                    geodata = extract_geodata(Image.open(path), fallback_waypoints)
                    extracted_data.append((file, geodata.date, geodata.latitude, geodata.longitude))
                except Exception as e:
                    print(f"Error extrating exif data from {file}: {e}")

        cur.executemany("INSERT OR REPLACE INTO Photodata VALUES(?,?,?,?)", extracted_data)
        con.commit()
        con.close()
        update_end = time.time()
        print(f"Update photo geolocation in {update_end - update_start:.1f} seconds")
