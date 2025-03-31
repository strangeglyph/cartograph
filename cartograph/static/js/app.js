const PCT_NW_CORNER = L.latLng(48.95153015463715, -125.363701636093);
const PCT_SE_CORNER = L.latLng(32.54702363909737, -115.65178765699379);
const BOUNDS = L.latLngBounds(PCT_NW_CORNER, PCT_SE_CORNER);

const MAP_OPTS = {
  zoomSnap: 0.25,
};

const ICON_WIDTH = 1185 / 25.0;
const ICON_HEIGHT = 1607 / 25.0;

const HIKER_ICON = L.icon({
  iconUrl: '/static/img/hiker.svg',
  iconSize: [ICON_WIDTH, ICON_HEIGHT],
  iconAnchor: [ICON_WIDTH/2.0, ICON_HEIGHT],
  popupAnchor: [0, 0],
});
const CAMERA_ICON = L.icon({
  iconUrl: '/static/img/camera.svg',
  iconSize: [ICON_WIDTH/2.0, ICON_HEIGHT/2.0],
  iconAnchor: [ICON_WIDTH/4.0, ICON_HEIGHT/2.0],
  popupAnchor: [0, 0],
});

var map = L.map('map', MAP_OPTS).fitBounds(BOUNDS);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

console.log("Map initialized");




function slideshowGetActiveIdx(entries) {
  var currentActiveIdx = 0;
  while (currentActiveIdx < entries.length) {
    let entry = entries[currentActiveIdx];
    if (!entry.classList.contains("hidden")) {
      return currentActiveIdx;
    }
    currentActiveIdx += 1;
  }

  return 0;
}

function slideshowUpdate(slideshowId, direction) {
  let slideshow = document.querySelector(`#${slideshowId}`);
  let entries = slideshow.querySelectorAll(".slideshow-entry");

  var idx = slideshowGetActiveIdx(entries);
  var nextIdx = (idx + direction + entries.length) % entries.length;
  entries[idx].classList.add("hidden");
  entries[nextIdx].classList.remove("hidden");
}


function createPopupSlideshow(photo_datum) {
  console.log("Creating popup slideshow");
  let cleanLat = photo_datum.position[0].toString().replace('.', '--');
  let cleanLng = photo_datum.position[1].toString().replace('.', '--');
  let id = `slideshow---${cleanLat}---${cleanLng}`;

  function makeEntry(photo, is_first) {
    let extra_classes = "";
    if (!is_first) extra_classes = "hidden";

    return `
        <div class="slideshow-entry ${extra_classes}">
            <img class="slideshow-img" src="/static/img/photos/${photo.path}" alt="${photo.desc}"/>
            <span class="slideshow-text">${photo.desc}</span>
        </div>
    `;
  }

  let entries = "";
  let is_first = true;
  for (const photo of photo_datum.photos) {
    entries += makeEntry(photo, is_first);
    is_first = false;
  }

  return `
    <div id="${id}" class="slideshow">
        <button onclick="slideshowUpdate('${id}', -1)">&lt;</button>
        ${entries}
        <button onclick="slideshowUpdate('${id}', 1)">&gt;</button>
     </div>
  `;
}

for (let photo_datum of PHOTO_DATA) {
  console.log("Adding photo datum", photo_datum)
  L.marker(photo_datum.position, {icon: CAMERA_ICON})
    .bindPopup(createPopupSlideshow(photo_datum), {maxWidth: "auto"})
    .addTo(map);
}



var animCtrlOpts = {};
var animMotionOpts = {
  duration: 8000,
};
var animMarkerOpts = {
  icon: HIKER_ICON
}
var pathAnim = L.motion.polyline(WAYPOINTS, animCtrlOpts, animMotionOpts, animMarkerOpts);
pathAnim.addTo(map);

function playButtonPressed() {
  console.log("Play/Pause")
  pathAnim.motionToggle();
}

function resetButtonPressed() {
  console.log("Reset")
  pathAnim.motionStop();
  pathAnim.motionStart();
  pathAnim.motionStop();
}
