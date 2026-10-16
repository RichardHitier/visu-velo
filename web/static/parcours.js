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

function fillSelect(select, values) {
    for (const value of values) select.add(new Option(value, value));
}

function numberOrNull(value) {
    return value === "" ? null : Number(value);
}

function readFilters(form) {
    const f = form.elements;
    return {
        activity: f.activity.value,
        year: f.year.value,
        loopType: f.loop_type.value,
        kmMin: numberOrNull(f.km_min.value),
        kmMax: numberOrNull(f.km_max.value),
        dplusMin: numberOrNull(f.dplus_min.value),
        dplusMax: numberOrNull(f.dplus_max.value),
        inView: f.in_view.checked,
    };
}

// True when value lies in [min, max]; null bounds are open, null value fails a bound.
function inRange(value, min, max) {
    if (min === null && max === null) return true;
    if (value == null) return false;
    return (min === null || value >= min) && (max === null || value <= max);
}

function matches(route, f, mapBounds) {
    return (
        (!f.activity || route.activity === f.activity) &&
        (!f.year || route.date.startsWith(f.year)) &&
        (!f.loopType || route.loop_type === f.loopType) &&
        inRange(route.distance_km, f.kmMin, f.kmMax) &&
        inRange(route.dplus, f.dplusMin, f.dplusMax) &&
        (!f.inView || mapBounds.intersects(route.layer.getBounds()))
    );
}

function compareRoutes(key, dir) {
    return (a, b) => {
        const x = a[key];
        const y = b[key];
        if (x == null) return 1; // nulls always last
        if (y == null) return -1;
        const order = typeof x === "string" ? x.localeCompare(y, "fr") : x - y;
        return dir * order;
    };
}

function rowHtml(route) {
    const color = ACTIVITY_COLORS[route.activity] || DEFAULT_COLOR;
    return `<tr data-id="${route.id}">
        <td><i style="background:${color}"></i>${escapeHtml(route.name)}</td>
        <td>${route.date}</td>
        <td class="num">${route.distance_km}</td>
        <td class="num">${route.dplus ?? ""}</td>
    </tr>`;
}

async function main() {
    const map = L.map("map");
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    const routes = await (await fetch("/api/routes")).json();
    const byId = new Map(routes.map((r) => [String(r.id), r]));
    const form = document.getElementById("filters");
    const tbody = document.querySelector("#routes tbody");
    const headers = document.querySelectorAll("#routes th[data-sort]");
    const count = document.getElementById("count");
    const sort = { key: "date", dir: -1 };
    let selectedId = null;

    function rowOf(route) {
        return tbody.querySelector(`tr[data-id="${route.id}"]`);
    }

    function selectRow(route) {
        tbody.querySelector("tr.selected")?.classList.remove("selected");
        selectedId = String(route.id);
        const row = rowOf(route);
        row?.classList.add("selected");
        row?.scrollIntoView({ block: "nearest" });
    }

    const group = L.featureGroup().addTo(map);
    for (const route of routes) {
        const color = ACTIVITY_COLORS[route.activity] || DEFAULT_COLOR;
        const line = L.polyline(decodePolyline(route.polyline), { color, ...BASE_STYLE });
        line.bindPopup(popupHtml(route));
        line.bindTooltip(`${route.name} · ${route.distance_km} km`, { sticky: true });
        line.on("mouseover", () => line.setStyle(HIGHLIGHT_STYLE).bringToFront());
        line.on("mouseout", () => line.setStyle(BASE_STYLE));
        line.on("click", () => selectRow(route));
        route.layer = line;
        line.addTo(group);
    }

    fillSelect(form.elements.activity, [...new Set(routes.map((r) => r.activity))].sort());
    fillSelect(
        form.elements.year,
        [...new Set(routes.map((r) => r.date.slice(0, 4)))].sort().reverse(),
    );

    // Show matching routes on the map and in the sorted table.
    function render() {
        const filters = readFilters(form);
        const bounds = map.getBounds();
        const shown = routes.filter((route) => matches(route, filters, bounds));
        const shownIds = new Set(shown.map((r) => r.id));
        for (const route of routes) {
            if (shownIds.has(route.id)) group.addLayer(route.layer);
            else group.removeLayer(route.layer);
        }
        shown.sort(compareRoutes(sort.key, sort.dir));
        tbody.innerHTML = shown.map(rowHtml).join("");
        if (selectedId) rowOf({ id: selectedId })?.classList.add("selected");
        for (const th of headers) {
            th.classList.toggle("sorted-asc", th.dataset.sort === sort.key && sort.dir === 1);
            th.classList.toggle("sorted-desc", th.dataset.sort === sort.key && sort.dir === -1);
        }
        count.textContent = `${shown.length} / ${routes.length} parcours`;
    }

    form.addEventListener("input", render);
    form.addEventListener("submit", (event) => event.preventDefault());
    // The reset event fires before fields are cleared.
    form.addEventListener("reset", () => setTimeout(render));

    for (const th of headers) {
        th.addEventListener("click", () => {
            const key = th.dataset.sort;
            // Text sorts ascending first, numbers and dates descending first.
            if (sort.key === key) sort.dir = -sort.dir;
            else sort.dir = key === "name" ? 1 : -1;
            sort.key = key;
            render();
        });
    }

    function routeOfEvent(event) {
        const row = event.target.closest("tr[data-id]");
        return row ? byId.get(row.dataset.id) : null;
    }

    tbody.addEventListener("mouseover", (event) => {
        routeOfEvent(event)?.layer.setStyle(HIGHLIGHT_STYLE).bringToFront();
    });
    tbody.addEventListener("mouseout", (event) => {
        routeOfEvent(event)?.layer.setStyle(BASE_STYLE);
    });
    tbody.addEventListener("click", (event) => {
        const route = routeOfEvent(event);
        if (!route) return;
        selectRow(route);
        map.fitBounds(route.layer.getBounds(), { padding: [30, 30] });
        route.layer.openPopup();
    });

    const view = loadView();
    if (view) map.setView([view.lat, view.lng], view.zoom);
    else if (routes.length) map.fitBounds(group.getBounds());
    else map.setView([43.06, 2.22], 10);
    map.on("moveend", () => {
        saveView(map);
        if (form.elements.in_view.checked) render();
    });
    addLegend(map, routes);
    render();
}

main();
