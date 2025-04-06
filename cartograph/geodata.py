import datetime
from threading import Thread
from time import sleep
from typing import Optional, List

import dateparser
import imaplib
import email
import re
from email.message import Message


class DatedLatLng():
    def __init__(self, date: datetime.datetime, latitude: float, longitude: float):
        self.date = date
        self.latitude = latitude
        self.longitude = longitude


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
        self.geodata: List[DatedLatLng] = []

    def update(self):
        result = []
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

        print(f"{len(result)} data points extracted")
        self.geodata = sorted(result, key=lambda latlng: latlng.date)


class GeodataThread(Thread):
    def __init__(self, geodata_client: GeodataClient, minutes: int):
        super().__init__()
        self.geodata_client = geodata_client
        self.minutes = minutes

    def run(self):
        while True:
            sleep(self.minutes * 60)
            self.geodata_client.update()
