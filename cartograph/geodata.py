import sqlite3
import time
from threading import Thread
from time import sleep
from typing import Optional, List

import dateparser
import imaplib
import email
import re
from email.message import Message

from cartograph.latlng import DatedLatLng


def get_plain_body(msg: Message) -> str:
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            charset = part.get_param("charset", "ASCII")
            return part.get_payload(decode=True).decode(charset)
    return None


def geodata_from_message(msg: Message) -> Optional[DatedLatLng]:
    # if not "no.reply.inreach@garmin.com" in msg["From"]:
    #    return None

    body = get_plain_body(msg)
    if not body:
        return None

    pattern = re.compile(r"Lat (?P<lat>\S+) Lon (?P<lng>\S+)")
    match = pattern.search(body)

    if not match:
        return None

    date_str = msg["Date"]
    if date_str[-6:] == " (UTC)":
        date_str = date_str[:-6]
    date = dateparser.parse(date_str)
    return DatedLatLng(date, float(match.group("lat")), float(match.group("lng")))


class GeodataClient:
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password

    def update(self) -> List[DatedLatLng]:
        result = []
        start = time.time()
        print(f"Connecting to {self.host}")
        with imaplib.IMAP4_SSL(self.host) as mail:
            print(f"Authenticating as {self.user} with {self.password}")
            mail.login(self.user, self.password)
            mail.enable('UTF8=ACCEPT')
            mail.select('inbox')

            # Search for all email messages in the inbox
            status, data = mail.search(None, 'ALL')

            # Iterate through each email message and print its contents
            msgIds = data[0].split()
            print(f"Found {len(msgIds)} messages in inbox")

            for num in msgIds:
                status, data = mail.fetch(num, '(RFC822)')
                email_message = email.message_from_bytes(data[0][1])
                geodata = geodata_from_message(email_message)
                if geodata:
                    result.append(geodata)

        end = time.time()
        print(f"{len(result)} data points extracted in {end - start:.1f} seconds")
        return sorted(result, key=lambda latlng: latlng.date)


class GeodataThread(Thread):
    def __init__(self, geodata_client: GeodataClient, minutes: int, db_path: str):
        super().__init__()
        self.geodata_client = geodata_client
        self.minutes = minutes
        self.db_path = db_path
        con = sqlite3.connect(db_path)
        con.execute("CREATE TABLE IF NOT EXISTS Geodata(date PRIMARY KEY, latitude, longitude)")
        con.close()

    def run(self):
        while True:
            try:
                data = [(it.date, it.latitude, it.longitude) for it in self.geodata_client.update()]
                con = sqlite3.connect(self.db_path)
                con.executemany("INSERT OR REPLACE INTO Geodata VALUES(:date, :latitude, :longitude)", data)
                con.commit()
                con.close()
            except Exception as e:
                print(f"[cartograph:geo] Error - {e}")
            sleep(self.minutes * 60)
