import React, { useEffect, useRef, useState, useCallback } from "react";
import L from "leaflet";
import { Search, MapPin, Loader2, Check, LocateFixed, AlertTriangle } from "lucide-react";
import { useI18n } from "../i18n";

// ---- Geocoding provider abstraction (swap Nominatim for Google/Mapbox later) ----
import api from "../lib/api";
const orangeIcon = L.divIcon({
  className: "",
  html: `<div style="transform:translate(-50%,-100%)"><svg width="34" height="44" viewBox="0 0 34 44" xmlns="http://www.w3.org/2000/svg"><path d="M17 0C7.6 0 0 7.6 0 17c0 12 17 27 17 27s17-15 17-27C34 7.6 26.4 0 17 0z" fill="#F1701E"/><circle cx="17" cy="17" r="6.5" fill="#fff"/></svg></div>`,
  iconSize: [34, 44], iconAnchor: [17, 44],
});

const OMAN_CENTER = [23.588, 58.3829];
// simple in-memory cache of reverse-geocoded results (keyed by rounded coord + lang)
const addrCache = {};

// OSM raster tiles with a resilience fallback. The primary source is the standard
// OpenStreetMap tile server; if tile requests keep failing (some networks/proxies
// block tile.openstreetmap.org), we transparently switch to CARTO basemaps, which
// are also free OSM-data raster tiles (no API key, same Leaflet stack).
const TILE_SOURCES = [
  { url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", attribution: "© OpenStreetMap" },
  { url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png", attribution: "© OpenStreetMap © CARTO" },
];

function addResilientTiles(map, onReady) {
  let idx = 0;
  let layer = null;
  let errors = 0;
  let loaded = false;
  const mount = () => {
    if (layer) map.removeLayer(layer);
    const src = TILE_SOURCES[idx];
    layer = L.tileLayer(src.url, { attribution: src.attribution, maxZoom: 19, subdomains: idx === 0 ? "abc" : "abcd" });
    layer.on("load", () => { loaded = true; onReady && onReady(); });
    layer.on("tileerror", () => {
      errors += 1;
      // If tiles keep failing and nothing loaded yet, try the next source once.
      if (!loaded && errors >= 4 && idx < TILE_SOURCES.length - 1) {
        idx += 1; errors = 0; mount();
      }
    });
    layer.addTo(map);
  };
  mount();
  return () => loaded;
}

// Build the best human-readable label from Nominatim address components.
// Prefers road / neighbourhood / suburb / village / town / city / governorate / country.
// Falls back to display_name — never raw coordinates.
function composeAddress(a, displayName) {
  if (!a) return { formatted: displayName || "", city: "", area: "", country: "" };
  const road = a.road || a.pedestrian || a.footway || a.residential_road || "";
  const area = a.neighbourhood || a.suburb || a.quarter || a.residential || a.city_district || a.hamlet || "";
  const city = a.city || a.town || a.village || a.municipality || a.county || a.state_district || "";
  const governorate = a.state || a.region || a.province || "";
  const country = a.country || "";
  let parts = [road, area, city, country].filter(Boolean);
  if (!road && !area && !city) parts = [governorate, country].filter(Boolean);
  // de-duplicate while preserving order
  const seen = new Set();
  const clean = parts.filter((p) => (seen.has(p) ? false : (seen.add(p), true)));
  return {
    formatted: clean.join("، ") || displayName || "",
    city: city || area || governorate || "",
    area: area || road || "",
    country,
  };
}

const geoProvider = {
  async reverse(lat, lng, lang = "ar", signal) {
    const key = `${lat.toFixed(5)},${lng.toFixed(5)},${lang}`;
    if (addrCache[key]) return addrCache[key];
    // server-side proxy to OSM Nominatim (avoids browser-side blocks/CORS/UA issues)
    const { data } = await api.get("/geo/reverse", { params: { lat, lng, lang }, signal });
    if (!data || !data.display_name && !data.address) throw new Error("reverse_empty");
    const comp = composeAddress(data.address, data.display_name);
    const out = { address: comp.formatted, city: comp.city, area: comp.area, country: comp.country };
    if (out.address) addrCache[key] = out;
    return out;
  },
  async search(q, lang = "ar", signal) {
    const { data } = await api.get("/geo/search", { params: { q, lang }, signal });
    return Array.isArray(data) ? data : [];
  },
};

export function MapPicker({ value, onConfirm, testIdPrefix = "map", accentConfirm = true, confirmLabel }) {
  const { t, lang } = useI18n();
  const mapEl = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(false);
  const [selected, setSelected] = useState(value || null);
  const [resolving, setResolving] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState(false);
  const [locating, setLocating] = useState(false);
  const [resolveError, setResolveError] = useState(false);
  const reqSeq = useRef(0);
  const abortRef = useRef(null);
  const lastCoord = useRef(null);

  const setMarker = useCallback(async (lat, lng, known) => {
    if (!mapRef.current) return;
    if (markerRef.current) markerRef.current.setLatLng([lat, lng]);
    else {
      markerRef.current = L.marker([lat, lng], { icon: orangeIcon, draggable: true }).addTo(mapRef.current);
      markerRef.current.on("dragend", async (e) => {
        const p = e.target.getLatLng();
        await resolve(p.lat, p.lng);
      });
    }
    mapRef.current.setView([lat, lng], 14);
    if (known) { setSelected({ lat, lng, ...known }); return; }
    await resolve(lat, lng);
    // eslint-disable-next-line
  }, [lang]);

  const resolve = useCallback(async (lat, lng) => {
    const myId = ++reqSeq.current;
    lastCoord.current = { lat, lng };
    // show the pin immediately, clear any stale label while we resolve
    setSelected((s) => ({ ...(s || {}), lat, lng, address: "", city: "", area: "", country: "" }));
    setResolving(true);
    setResolveError(false);
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const attempt = async (isRetry) => {
      try {
        const geo = await geoProvider.reverse(lat, lng, lang, ctrl.signal);
        if (myId !== reqSeq.current) return; // a newer selection superseded this one
        setSelected({ lat, lng, ...geo });
        setResolveError(false);
      } catch (err) {
        if (myId !== reqSeq.current) return; // stale / aborted — ignore
        if (!isRetry) {
          await new Promise((r) => setTimeout(r, 700));
          if (myId !== reqSeq.current) return;
          return attempt(true);
        }
        // give up gracefully — keep coords internally, flag the error, no raw-coord label
        setSelected((s) => ({ ...(s || {}), lat, lng }));
        setResolveError(true);
      }
    };

    try {
      await attempt(false);
    } finally {
      if (myId === reqSeq.current) setResolving(false);
    }
  }, [lang]);

  const retryResolve = useCallback(() => {
    if (lastCoord.current) resolve(lastCoord.current.lat, lastCoord.current.lng);
  }, [resolve]);

  // ensure a human-readable address is stored — never raw coordinates
  const finalizeSelected = (s) => {
    if (s.address && s.address.trim()) return s;
    const fallback = [s.area, s.city, s.country].filter(Boolean).join("، ");
    return { ...s, address: fallback };
  };

  const initMap = useCallback(() => {
    if (mapRef.current || !mapEl.current) return;
    setMapError(false);
    try {
      const map = L.map(mapEl.current, { zoomControl: true }).setView(
        value ? [value.lat, value.lng] : OMAN_CENTER, value ? 14 : 7
      );
      let loaded = false;
      const isLoaded = addResilientTiles(map, () => { loaded = true; setMapReady(true); });
      map.on("click", (e) => setMarker(e.latlng.lat, e.latlng.lng));
      mapRef.current = map;
      if (value) setMarker(value.lat, value.lng, { address: value.address, city: value.city, area: value.area, country: value.country });
      setTimeout(() => { map.invalidateSize(); if (!loaded && !isLoaded()) setMapReady(true); }, 900);
    } catch {
      setMapError(true);
    }
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    initMap();
    return () => { if (abortRef.current) abortRef.current.abort(); if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; markerRef.current = null; } };
    // eslint-disable-next-line
  }, []);

  const doSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setSearching(true); setSearchError(false);
    try { setResults(await geoProvider.search(query, lang)); }
    catch { setSearchError(true); setResults([]); }
    finally { setSearching(false); }
  };

  const pickResult = (r) => {
    setResults([]);
    setQuery(r.display_name.split(",")[0]);
    const comp = composeAddress(r.address);
    setMarker(parseFloat(r.lat), parseFloat(r.lon), {
      address: comp?.formatted || r.display_name, city: comp?.city || "", area: comp?.area || "", country: comp?.country || "",
    });
  };

  const useCurrent = () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => { setLocating(false); setMarker(pos.coords.latitude, pos.coords.longitude); },
      () => setLocating(false),
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  const retryMap = () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } setMapReady(false); initMap(); };

  return (
    <div className="space-y-3" data-testid={`${testIdPrefix}-picker`}>
      <form onSubmit={doSearch} className="relative">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
            <input data-testid={`${testIdPrefix}-search-input`} value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder={t("shipment.searchLocation")}
              className="w-full bg-white border border-slate-300 focus:border-[#F1701E] focus:ring-2 focus:ring-[#F1701E]/20 rounded-lg ps-9 pe-3 py-2.5 text-sm outline-none" />
          </div>
          <button type="submit" data-testid={`${testIdPrefix}-search-btn`} className="bg-[#16233A] hover:bg-[#0E1726] text-white font-semibold px-4 rounded-lg text-sm flex items-center gap-2">
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}<span className="hidden sm:inline">{t("common.search")}</span>
          </button>
        </div>
        {results.length > 0 && (
          <div className="absolute z-[500] mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-56 overflow-auto">
            {results.map((r, i) => (
              <button type="button" key={i} data-testid={`${testIdPrefix}-result-${i}`} onClick={() => pickResult(r)}
                className="w-full text-start px-3 py-2 hover:bg-slate-50 text-sm border-b last:border-0 flex gap-2">
                <MapPin className="w-4 h-4 text-[#F1701E] shrink-0 mt-0.5" /><span className="truncate">{r.display_name}</span>
              </button>
            ))}
          </div>
        )}
      </form>

      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-slate-400 flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-[#F1701E]" /> {t("shipment.tapMapHint")}</p>
        <button type="button" onClick={useCurrent} data-testid={`${testIdPrefix}-current-btn`} className="text-xs font-semibold text-[#16233A] flex items-center gap-1.5 hover:text-[#F1701E]">
          {locating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <LocateFixed className="w-3.5 h-3.5" />} {locating ? t("p11.map.locating") : t("p11.map.useCurrent")}
        </button>
      </div>
      {searchError && <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2" data-testid={`${testIdPrefix}-search-error`}>{t("shipment.searchUnavailable")}</p>}

      <div className="relative w-full h-[320px] md:h-[380px] rounded-xl border border-slate-300 overflow-hidden shadow-inner bg-slate-100">
        <div ref={mapEl} className="w-full h-full" data-testid={`${testIdPrefix}-canvas`} />
        {!mapReady && !mapError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-slate-100/80 z-[400]" data-testid={`${testIdPrefix}-loading`}>
            <Loader2 className="w-6 h-6 animate-spin text-[#F1701E]" /><span className="text-sm text-slate-500">{t("p11.map.loading")}</span>
          </div>
        )}
        {mapError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-slate-100 z-[400]" data-testid={`${testIdPrefix}-error`}>
            <AlertTriangle className="w-7 h-7 text-amber-500" /><span className="text-sm text-slate-600">{t("p11.map.error")}</span>
            <button onClick={retryMap} className="text-sm font-semibold text-[#F1701E]">{t("p11.map.retry")}</button>
          </div>
        )}
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
        <div className="text-xs font-semibold text-slate-500 mb-1">{t("shipment.selectedAddress")}</div>
        {resolving ? (
          <div className="flex items-center gap-2 text-sm text-slate-500"><Loader2 className="w-4 h-4 animate-spin" /> {t("p11.map.resolving")}</div>
        ) : selected ? (
          <div data-testid={`${testIdPrefix}-selected-address`} className="text-sm text-slate-800">
            <span className="font-semibold">{selected.address || t("p11.map.unnamed")}</span>
            {(selected.area || selected.city || selected.country) && (
              <span className="block text-xs text-slate-500 mt-0.5">{[selected.area, selected.city, selected.country].filter(Boolean).join("، ")}</span>
            )}
            {resolveError && (
              <span className="mt-1.5 flex items-center gap-2 text-xs text-amber-600" data-testid={`${testIdPrefix}-resolve-error`}>
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> {t("p11.map.resolveError")}
                <button type="button" onClick={retryResolve} data-testid={`${testIdPrefix}-resolve-retry`} className="font-semibold text-[#F1701E] underline">{t("p11.map.retry")}</button>
              </span>
            )}
            <span className="block font-mono text-[11px] text-slate-400 mt-1 force-ltr">{t("p11.map.coordinates")}: {selected.lat.toFixed(5)}, {selected.lng.toFixed(5)}</span>
          </div>
        ) : <div className="text-sm text-slate-400">{t("shipment.searchLocation")}</div>}
      </div>

      <button type="button" disabled={!selected} data-testid={`${testIdPrefix}-confirm-btn`}
        onClick={() => selected && onConfirm(finalizeSelected(selected))}
        className={`w-full font-semibold py-2.5 rounded-lg flex items-center justify-center gap-2 disabled:opacity-40 transition-colors ${accentConfirm ? "bg-[#F1701E] hover:bg-[#D95E0E] text-white" : "bg-[#16233A] hover:bg-[#0E1726] text-white"}`}>
        <Check className="w-4 h-4" /> {confirmLabel || t("common.confirm")}
      </button>
    </div>
  );
}

export function StaticRouteMap({ pickup, delivery, height = 260 }) {
  const mapEl = useRef(null);
  const mapRef = useRef(null);
  useEffect(() => {
    if (mapRef.current || !mapEl.current) return;
    const map = L.map(mapEl.current, { zoomControl: false, dragging: true, scrollWheelZoom: false }).setView(OMAN_CENTER, 7);
    addResilientTiles(map);
    const pts = [];
    if (pickup) { L.marker([pickup.lat, pickup.lng], { icon: orangeIcon }).addTo(map); pts.push([pickup.lat, pickup.lng]); }
    if (delivery) {
      const navyIcon = L.divIcon({ className: "", html: `<div style="transform:translate(-50%,-100%)"><svg width="34" height="44" viewBox="0 0 34 44" xmlns="http://www.w3.org/2000/svg"><path d="M17 0C7.6 0 0 7.6 0 17c0 12 17 27 17 27s17-15 17-27C34 7.6 26.4 0 17 0z" fill="#16233A"/><circle cx="17" cy="17" r="6.5" fill="#fff"/></svg></div>`, iconSize: [34, 44], iconAnchor: [17, 44] });
      L.marker([delivery.lat, delivery.lng], { icon: navyIcon }).addTo(map); pts.push([delivery.lat, delivery.lng]);
    }
    if (pts.length === 2) { L.polyline(pts, { color: "#F1701E", weight: 3, dashArray: "6 8" }).addTo(map); map.fitBounds(pts, { padding: [40, 40] }); }
    else if (pts.length === 1) map.setView(pts[0], 12);
    setTimeout(() => map.invalidateSize(), 300);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
    // eslint-disable-next-line
  }, []);
  return (
    <div className="relative w-full rounded-xl border border-slate-300 overflow-hidden shadow-inner bg-slate-100" style={{ height }}>
      <div ref={mapEl} className="w-full h-full" data-testid="static-route-map" />
    </div>
  );
}
