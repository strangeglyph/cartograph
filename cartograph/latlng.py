import datetime
import math


class DatedLatLng:
    def __init__(self, date: datetime.datetime, latitude: float, longitude: float):
        self.date = date
        self.latitude = latitude
        self.longitude = longitude

    def sqdist(self, other: "DatedLatLng") -> float:
        dlat = self.latitude - other.latitude
        dlng = self.longitude - other.longitude
        return dlat*dlat + dlng*dlng

    def dist(self, other: "DatedLatLng") -> float:
        return math.sqrt(self.sqdist(other))
