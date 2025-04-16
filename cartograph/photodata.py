import os
import sqlite3
import time
from threading import Thread
from time import sleep
import datetime

from PIL import Image, ExifTags
from webdav3.client import Client

from cartograph.latlng import DatedLatLng

GPS_KEY = 34853
GPS_LAT_REF = 1
GPS_LNG_REF = 3
GPS_LAT_DATA = 2
GPS_LNG_DATA = 4
DATETIME_KEY = 306


def extract_geodata(img: Image):
    exif = img.getexif()
    gps_info = exif.get_ifd(GPS_KEY)
    lat_deg, lat_min, lat_sec = gps_info[GPS_LAT_DATA]
    lat_ddeg = lat_deg + (lat_min / 60) + (lat_sec / 3600)
    if gps_info[GPS_LAT_REF] == "S":
        lat_ddeg = -lat_ddeg
    # truncate
    lat_ddeg = int(lat_ddeg * 1000) / 1000

    lng_deg, lng_min, lng_sec = gps_info[GPS_LNG_DATA]
    lng_ddeg = lng_deg + (lng_min / 60) + (lng_sec / 3600)
    if gps_info[GPS_LNG_REF] == "W":
        lng_ddeg = -lng_ddeg
    # truncate
    lng_ddeg = int(lng_ddeg * 1000) / 1000

    date_str = exif[DATETIME_KEY]
    timestamp = datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')

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
        updated = self.client.pull(remote_directory=self.remote_path, local_directory=self.local_path)
        sync_end = time.time()
        print(f"Synced files in {sync_end - sync_start:.1f} seconds")

        update_start = time.time()
        extracted_data = []
        for file in os.listdir(self.local_path):
            path = os.path.join(self.local_path, file)
            if os.path.isfile(path):
                try:
                    geodata = extract_geodata(Image.open(path))
                    extracted_data.append((file, geodata.date, geodata.latitude, geodata.longitude))
                except e:
                    print(f"Error extrating exif data from {file}: {e}")
        con = sqlite3.connect(self.db_path)
        con.executemany("INSERT OR REPLACE INTO Photodata VALUES(?,?,?,?)", extracted_data)
        con.commit()
        con.close()
        update_end = time.time()
        print(f"Update photo geolocation in {update_end - update_start:.1f} seconds")
