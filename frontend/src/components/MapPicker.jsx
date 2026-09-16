import React, { useEffect, useRef, useState, useCallback } from "react";
import L from "leaflet";
import { Search, MapPin, Loader2, Check } from "lucide-react";
import { useI18n } from "../i18n";

// Fix default marker icons (bundler strips the asset paths)
const orangeIcon = L.divIcon({
  className: "",
  html: `<div style="transform:translate(-50%,-100%)"><svg width="34" height="44" viewBox="0 0 34 44" xmlns="http://www.w3.org/2000/svg"><path d="M17 0C7.6 0 0 7.6 0 17c0 12 17 27 17 27s17-15 17-27C34 7.6 26.4 0 17 0z" fill="#F1701E"/><circle cx="17" cy="17" r="6.5" fill="#fff"/></svg></div>`,
  iconSize: [34, 44],
  iconAnchor: [17, 44],
});

const OMAN_CENTER = [23.588, 58.3829];

async function reverseGeocode(lat, lng) {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&accept-language=ar`,
      { headers: { "Accept-Language": "ar" } }
    );
    const data = await res.json();
    return data.display_name || "";
  } catch {
    return "";
  }
}

async function searchPlaces(q) {
  const res = await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&countrycodes=om&limit=6&q=${encodeURIComponent(q)}`
  );
  if (!res.ok) throw new Error("search_failed");
  return await res.json();
}

export function MapPicker({ value, onConfirm, testIdPrefix = "map", accentConfirm = true, confirmLabel }) {
  const { t } = useI18n();
  const mapEl = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(false);
  const [selected, setSelected] = useState(value || null);
  const [geoLoading, setGeoLoading] = useState(false);

  const setMarker = useCallback(async (lat, lng, addr) => {
    if (!mapRef.current) return;
    if (markerRef.current) {
      markerRef.current.setLatLng([lat, lng]);
    } else {
      markerRef.current = L.marker([lat, lng], { icon: orangeIcon, draggable: true }).addTo(mapRef.current);
      markerRef.current.on("dragend", async (e) => {
        const p = e.target.getLatLng();
        setGeoLoading(true);
        const address = await reverseGeocode(p.lat, p.lng);
        setGeoLoading(false);
        setSelected({ lat: p.lat, lng: p.lng, address });
      });
    }
    mapRef.current.setView([lat, lng], 13);
    if (addr !== undefined) {
      setSelected({ lat, lng, address: addr });
    } else {
      setGeoLoading(true);
      const address = await reverseGeocode(lat, lng);
      setGeoLoading(false);
      setSelected({ lat, lng, address });
    }
  }, []);

  useEffect(() => {
    if (mapRef.current || !mapEl.current) return;
    const map = L.map(mapEl.current, { zoomControl: true }).setView(
      value ? [value.lat, value.lng] : OMAN_CENTER,
      value ? 13 : 7
    );
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);
    map.on("click", (e) => setMarker(e.latlng.lat, e.latlng.lng));
    mapRef.current = map;
    if (value) setMarker(value.lat, value.lng, value.address);
    setTimeout(() => map.invalidateSize(), 200);
    return () => { map.remove(); mapRef.current = null; markerRef.current = null; };
    // eslint-disable-next-line
  }, []);

  const doSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearchError(false);
    try {
      const r = await searchPlaces(query);
      setResults(r);
    } catch {
      setSearchError(true);
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const pickResult = (r) => {
    setResults([]);
    setQuery(r.display_name.split(",")[0]);
    setMarker(parseFloat(r.lat), parseFloat(r.lon), r.display_name);
  };

  return (
    <div className="space-y-3" data-testid={`${testIdPrefix}-picker`}>
      <form onSubmit={doSearch} className="relative">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
            <input
              data-testid={`${testIdPrefix}-search-input`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("shipment.searchLocation")}
              className="w-full bg-white border border-slate-300 focus:border-[#F1701E] focus:ring-2 focus:ring-[#F1701E]/20 rounded-lg ps-9 pe-3 py-2.5 text-sm outline-none"
            />
          </div>
          <button
            type="submit"
            data-testid={`${testIdPrefix}-search-btn`}
            className="bg-[#16233A] hover:bg-[#0E1726] text-white font-semibold px-4 rounded-lg text-sm flex items-center gap-2"
          >
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {t("common.search")}
          </button>
        </div>
        {results.length > 0 && (
          <div className="absolute z-[500] mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-56 overflow-auto">
            {results.map((r, i) => (
              <button
                type="button"
                key={i}
                data-testid={`${testIdPrefix}-result-${i}`}
                onClick={() => pickResult(r)}
                className="w-full text-start px-3 py-2 hover:bg-slate-50 text-sm border-b last:border-0 flex gap-2"
              >
                <MapPin className="w-4 h-4 text-[#F1701E] shrink-0 mt-0.5" />
                <span className="truncate">{r.display_name}</span>
              </button>
            ))}
          </div>
        )}
      </form>

      <p className="text-xs text-slate-400 flex items-center gap-1.5" data-testid={`${testIdPrefix}-hint`}>
        <MapPin className="w-3.5 h-3.5 text-[#F1701E]" /> {t("shipment.tapMapHint")}
      </p>
      {searchError && (
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2" data-testid={`${testIdPrefix}-search-error`}>
          {t("shipment.searchUnavailable")}
        </p>
      )}

      <div className="relative w-full h-[320px] md:h-[380px] rounded-xl border border-slate-300 overflow-hidden shadow-inner bg-slate-100">
        <div ref={mapEl} className="w-full h-full" data-testid={`${testIdPrefix}-canvas`} />
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
        <div className="text-xs font-semibold text-slate-500 mb-1">{t("shipment.selectedAddress")}</div>
        {geoLoading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500"><Loader2 className="w-4 h-4 animate-spin" /> {t("common.loading")}</div>
        ) : selected ? (
          <div data-testid={`${testIdPrefix}-selected-address`} className="text-sm text-slate-800">
            {selected.address || `${selected.lat.toFixed(5)}, ${selected.lng.toFixed(5)}`}
            <span className="block font-mono text-xs text-slate-400 mt-0.5 force-ltr">{selected.lat.toFixed(5)}, {selected.lng.toFixed(5)}</span>
          </div>
        ) : (
          <div className="text-sm text-slate-400">{t("shipment.searchLocation")}</div>
        )}
      </div>

      <button
        type="button"
        disabled={!selected}
        data-testid={`${testIdPrefix}-confirm-btn`}
        onClick={() => selected && onConfirm(selected)}
        className={`w-full font-semibold py-2.5 rounded-lg flex items-center justify-center gap-2 disabled:opacity-40 transition-colors ${
          accentConfirm ? "bg-[#F1701E] hover:bg-[#D95E0E] text-white" : "bg-[#16233A] hover:bg-[#0E1726] text-white"
        }`}
      >
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
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap", maxZoom: 19 }).addTo(map);
    const pts = [];
    if (pickup) { L.marker([pickup.lat, pickup.lng], { icon: orangeIcon }).addTo(map); pts.push([pickup.lat, pickup.lng]); }
    if (delivery) {
      const navyIcon = L.divIcon({ className: "", html: `<div style="transform:translate(-50%,-100%)"><svg width="34" height="44" viewBox="0 0 34 44" xmlns="http://www.w3.org/2000/svg"><path d="M17 0C7.6 0 0 7.6 0 17c0 12 17 27 17 27s17-15 17-27C34 7.6 26.4 0 17 0z" fill="#16233A"/><circle cx="17" cy="17" r="6.5" fill="#fff"/></svg></div>`, iconSize: [34, 44], iconAnchor: [17, 44] });
      L.marker([delivery.lat, delivery.lng], { icon: navyIcon }).addTo(map); pts.push([delivery.lat, delivery.lng]);
    }
    if (pts.length === 2) {
      L.polyline(pts, { color: "#F1701E", weight: 3, dashArray: "6 8" }).addTo(map);
      map.fitBounds(pts, { padding: [40, 40] });
    } else if (pts.length === 1) {
      map.setView(pts[0], 12);
    }
    setTimeout(() => map.invalidateSize(), 200);
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
