// Map of all OpenRunner routes, one polyline per route colored by activity.

const ACTIVITY_COLORS = {
    CYCLING: "#d7301f",
    CYCLING_MTB: "#8c510a",
    HIKING: "#1a9850",
    BACKCOUNTRY_SKIING: "#2166ac",
    SKI_TOURING: "#5e3c99",
};
const DEFAULT_COLOR = "#636363";
const BASE_STYLE = { weight: 3, opacity: 0.7 };
const HIGHLIGHT_STYLE = { weight: 6, opacity: 1 };
const VIEW_KEY = "parcours.mapView";

// Last saved {lat, lng, zoom}, or null when absent or storage unavailable.
function loadView() {
    try {
        const view = JSON.parse(localStorage.getItem(VIEW_KEY));
        return view && Number.isFinite(view.zoom) ? view : null;
    } catch {
        return null;
    }
}

function saveView(map) {
    const { lat, lng } = map.getCenter();
    try {
        localStorage.setItem(VIEW_KEY, JSON.stringify({ lat, lng, zoom: map.getZoom() }));
    } catch {
        // Storage blocked (private mode...): just don't remember the view.
    }
}

// Decode a Google encoded polyline (precision 5) into [[lat, lon], ...].
function decodePolyline(encoded) {
    const points = [];
    let index = 0;
    let lat = 0;
    let lon = 0;
    while (index < encoded.length) {
        for (const axis of [0, 1]) {
            let result = 0;
            let shift = 0;
            let byte;
            do {
                byte = encoded.charCodeAt(index++) - 63;
                result |= (byte & 0x1f) << shift;
                shift += 5;
            } while (byte >= 0x20);
            const delta = result & 1 ? ~(result >> 1) : result >> 1;
            if (axis === 0) lat += delta;
            else lon += delta;
        }
        points.push([lat / 1e5, lon / 1e5]);
    }
    return points;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text ?? "";
    return div.innerHTML;
}

function popupHtml(route) {
    const dplus = route.dplus == null ? "?" : route.dplus;
    const passes = route.passes.length
        ? "<ul>" +
          route.passes
              .map((p) => `<li>${escapeHtml(p.name)} (${p.altitude} m, km ${p.km})</li>`)
              .join("") +
          "</ul>"
        : "";
    return `<div class="route-popup">
        <h3>${escapeHtml(route.name)}</h3>
        ${route.distance_km} km · D+ ${dplus} m · ${route.date}<br>
        ${escapeHtml(route.start)}
        ${passes}
        <br><a href="https://www.openrunner.com/route-details/${route.id}" target="_blank" rel="noopener">OpenRunner</a>
    </div>`;
}

function addLegend(map, routes) {
    const counts = {};
    for (const route of routes) counts[route.activity] = (counts[route.activity] || 0) + 1;
    const legend = L.control({ position: "bottomright" });
    legend.onAdd = () => {
        const div = L.DomUtil.create("div", "legend");
        div.innerHTML = Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([activity, n]) => {
                const color = ACTIVITY_COLORS[activity] || DEFAULT_COLOR;
                return `<i style="background:${color}"></i>${activity} (${n})`;
            })
            .join("<br>");
        return div;
    };
    legend.addTo(map);
}

async function main() {
    const map = L.map("map");
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    const routes = await (await fetch("/api/routes")).json();
    document.getElementById("count").textContent = `${routes.length} parcours`;

    const group = L.featureGroup().addTo(map);
    for (const route of routes) {
        const color = ACTIVITY_COLORS[route.activity] || DEFAULT_COLOR;
        const line = L.polyline(decodePolyline(route.polyline), { color, ...BASE_STYLE });
        line.bindPopup(popupHtml(route));
        line.bindTooltip(`${route.name} · ${route.distance_km} km`, { sticky: true });
        line.on("mouseover", () => line.setStyle(HIGHLIGHT_STYLE).bringToFront());
        line.on("mouseout", () => line.setStyle(BASE_STYLE));
        line.addTo(group);
    }
    const view = loadView();
    if (view) map.setView([view.lat, view.lng], view.zoom);
    else if (routes.length) map.fitBounds(group.getBounds());
    else map.setView([43.06, 2.22], 10);
    map.on("moveend", () => saveView(map));
    addLegend(map, routes);
}

main();
