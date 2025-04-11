import datetime


class DatedLatLng():
    def __init__(self, date: datetime.datetime, latitude: float, longitude: float):
        self.date = date
        self.latitude = latitude
        self.longitude = longitude
