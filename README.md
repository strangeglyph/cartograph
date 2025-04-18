# Cartograph Website
### Overview
Cartograph uses Leaflet as an OSM map renderer. It then 
renders a hiking path and photo markers along that path. To this end,
two lists are injected by the rendering engine (Flask):
- `WAYPOINTS`, a list of objects with a `date : Date` and a `pos : L.LatLng` 
 attribute.
- `PHOTO_DATA` a list that contains one entry per path segment. Each entry is 
  itself a list of photo marker information, each object containing
  - `position : [float, float]`, the position of the marker as latitude-longitude pair
  - `main_index: int`, the segment index
  - `fraction: float`, the relative distance along the segment at which the marker should become visible in animation mode
  - `photos: [Photo]`, a list of `Photo` objects carrying the file path of the image file (relative to `/static/photos/`) 
     and an optional caption

The website is hosted as an WSGI app running flask. The app spins up two additional
threads
- `geodata.GeodataThread` connects to a mail server and does a quick and dirty check 
  for mails from Garmin's inReach system and tries to extract the GPS location
  found in those mails
- `photodata.PhotodataThread` connects to a webdav server, syncs a 
  specified directory containing the photos and tries to extract the EXIF
  GPS and time metadata. In case time data isn't found, we're doing a best-effort 
  parse based on the file name, and in the case the gps metadata isn't found
  we're currently placing the photo halfway on a segment based on the day the photo
  was taken

Both of these threads write their information into an SQLITE database since WSGI
apps don't like sharing data between threads, apparently.

On a request, that data is extracted from the DB and photos are grouped into 20
buckets per segment (based on distance to the two closest waypoints instead of date,
this is currently buggy but I haven't gotten around to fixing it yet).


### Icon Attribution
- Hiker: [Viglino](https://www.svgrepo.com/svg/399446/hiker)
- Camera: [Noah Jacobus](https://www.svgrepo.com/svg/535246/camera)
- PlayPause: [Dazzle UI](https://www.svgrepo.com/svg/532512/play-pause)
- Backwards Fast: [Dazzle UI](https://www.svgrepo.com/svg/532494/backward-fast)
- Backwards Step: [Dazzle UI](https://www.svgrepo.com/svg/532495/backward-step)