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
    iconAnchor: [ICON_WIDTH / 2.0, ICON_HEIGHT],
    popupAnchor: [0, 0],
});
const CAMERA_ICON = L.icon({
    iconUrl: '/static/img/camera.svg',
    iconSize: [ICON_WIDTH / 2.0, ICON_HEIGHT / 2.0],
    iconAnchor: [ICON_WIDTH / 4.0, ICON_HEIGHT / 2.0],
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


let PHOTO_GROUPS = [];
for (let i = 0; i < WAYPOINTS.length; i++) {
    let group = L.featureGroup();
    PHOTO_GROUPS.push(group);
    group.addTo(map);

    reinit_photo_group(i);
}

function reinit_photo_group(idx, max_fraction=1.0) {
    let group = PHOTO_GROUPS[idx];
    group.clearLayers();

    const segment_photo_list = PHOTO_DATA[idx];
    if (segment_photo_list == null) {
        return;
    }

    for (const photo_datum of segment_photo_list) {
        if (photo_datum.fraction > max_fraction) {
            break;
        }

        console.log(`photo group ${idx} datum ${photo_datum.fraction}/${max_fraction}`);

        L.marker(photo_datum.position, {icon: CAMERA_ICON})
            .bindPopup(createPopupSlideshow(photo_datum), {maxWidth: "auto"})
            .addTo(group);
    }
}


const WAYPOINT_POS = WAYPOINTS.map((point) => point.pos);
document.querySelector("#date-indicator").innerHTML = WAYPOINTS[WAYPOINTS.length - 1].date.toLocaleDateString("de-DE");


class LineAnim {
    constructor(points, layer, icon, segment_change_callback, fractional_update_callback) {
        this.points = points;
        this.layer = layer;
        this.segment_change_callback = segment_change_callback;
        this.fractional_update_callback = fractional_update_callback
        this.interval = null;
        this.currentIdx = 0;
        this.fractionToNext = 0.0;
        this.lastUpdate = Date.now();
        this.speed = 1; // segments per second
        this.running = false;
        this.marker = L.marker(points[0], {icon: icon}).addTo(layer);
        this.line = L.polyline([points[0]]).addTo(layer);
    }

    update() {
        const timeNow = Date.now();
        const delta = timeNow - this.lastUpdate;
        this.lastUpdate = timeNow;

        let fractProgress = delta / 1000.0 * this.speed;
        this.fractionToNext += fractProgress;
        if (this.fractionToNext >= 1.0) {
            // we could be skipping more than one segment if we're deprioritized by the browser
            // but to avoid straightening the line too much we catch up over several updates
            this.fractionToNext -= 1.0;
            this.currentIdx += 1;
            if (this.segment_change_callback != null) {
                this.segment_change_callback(this.currentIdx - 1, this.currentIdx);
            }
        }
        if (this.fractional_update_callback != null) {
            this.fractional_update_callback(this.currentIdx, this.fractionToNext)
        }

        if (this.currentIdx >= this.points.length - 1) {
            this.currentIdx = this.points.length - 1
            this.fractionToNext = 0.0
        }

        let nextPos;
        if (this.fractionToNext == 0.0) {
            nextPos = this.points[this.currentIdx];
        } else {
            const alpha = this.fractionToNext;
            const pointA = this.points[this.currentIdx];
            const pointB = this.points[this.currentIdx + 1];
            const lat = (1.0 - alpha) * pointA.lat + alpha * pointB.lat;
            const lng = (1.0 - alpha) * pointA.lng + alpha * pointB.lng;
            nextPos = L.latLng(lat, lng);
        }

        this.marker.setLatLng(nextPos);
        this.line.addLatLng(nextPos);

        if (this.atEnd()) {
            this.pause()
        }
    }

    atEnd() {
        return this.currentIdx >= this.points.length - 1;
    }

    reset() {
        const oldIdx = this.currentIdx;
        this.currentIdx = 0;
        this.fractionToNext = 0.0
        this.line.setLatLngs([]);
        if (this.segment_change_callback != null) {
            this.segment_change_callback(oldIdx, 0);
        }
        this.lastUpdate = Date.now();
        this.update();
    }

    toEnd() {
        const oldIdx = this.currentIdx;
        this.currentIdx = this.points.length - 1;
        this.fractionToNext = 0.0;
        this.line.setLatLngs(this.points);
        if (this.segment_change_callback != null) {
            this.segment_change_callback(oldIdx, this.points.length - 1);
        }
        this.lastUpdate = Date.now();
        this.update();
    }

    skipForward() {
        if (this.currentIdx < this.points.length - 1) {
            this.currentIdx += 1;
            this.fractionToNext = 0.0;
            if (this.segment_change_callback != null) {
                this.segment_change_callback(this.currentIdx - 1, this.currentIdx);
            }
        }
        this.lastUpdate = Date.now();
        this.update();
    }

    skipBackwards() {
        if (this.currentIdx > 0 && this.fractionToNext == 0.0) {
            this.currentIdx -= 1;
            if (this.segment_change_callback != null) {
                this.segment_change_callback(this.currentIdx + 1, this.currentIdx);
            }
        } else {
            this.fractionToNext = 0.0;
            if (this.fractional_update_callback != null) {
                this.fractional_update_callback(this.currentIdx, 0.0);
            }
        }
        this.line.setLatLngs(this.points.slice(0, this.currentIdx + 1));
        this.lastUpdate = Date.now();
        this.update();
    }

    start() {
        if (this.interval != null) {
            clearInterval(this.interval);
        }

        this.running = true;
        this.lastUpdate = Date.now();
        this.update();
        this.interval = setInterval(() => this.update(), 25);
    }

    stop() {
        if (this.interval != null) {
            clearInterval(this.interval);
        }

        this.running = false;
        this.interval = null;
        this.reset();
    }

    pause() {
        console.log("Pause requested")
        if (this.interval != null) {
            console.log(`Clearing interval ${this.interval}`)
            clearInterval(this.interval);
        }

        this.running = false;
    }
}

function segmentChange(oldIdx, newIdx) {
    document.getElementById("date-indicator").innerHTML = WAYPOINTS[newIdx].date.toLocaleDateString("de-DE");

    if (oldIdx < newIdx) {
        console.log(`bulk photo group fill ${oldIdx} - ${newIdx}`)
        for (let i = oldIdx; i < newIdx; i++) {
            reinit_photo_group(i);
        }
    } else {
        console.log(`bulk photo group clear ${oldIdx} - ${newIdx}`)
        for (let i = oldIdx; i >= newIdx; i--) {
            reinit_photo_group(i, 0.0);
        }
    }
}

function fractionalChange(idx, fraction) {
    console.log(`fractional photo group ${idx}@${fraction}`)
    reinit_photo_group(idx, fraction);
}

const ANIM_GROUP = L.featureGroup();
let anim = new LineAnim(WAYPOINT_POS, ANIM_GROUP, HIKER_ICON, segmentChange, fractionalChange);
anim.toEnd();
ANIM_GROUP.addTo(map);
map.fitBounds(anim.line.getBounds());

document.getElementById("playback-speed").value = "1";

function speedChange(box) {
    anim.speed = parseInt(box.value)
}

function resetButtonPressed() {
    anim.reset();
}

function stepBackPressed() {
    anim.skipBackwards();
}

function stepForwardPressed() {
    anim.skipForward();
}

function toEndPressed() {
    anim.toEnd();
}

function playPausePressed() {
    console.log("Play/pause pressed")
    if (anim.running) {
        console.log()
        anim.pause();
    } else {
        if (anim.atEnd()) {
            anim.reset();
        }
        anim.start();
    }
}