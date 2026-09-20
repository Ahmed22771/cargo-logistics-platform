import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Truck } from "lucide-react";
import { Card, Spinner, EmptyState, PageHeader, Input } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

const ACTIVE = new Set(["DRIVER_ASSIGNED", "PICKUP_ARRIVED", "PICKED_UP", "IN_TRANSIT", "DRIVER_ARRIVED_DESTINATION", "DELIVERED_PENDING_CONFIRMATION"]);
const UPCOMING = new Set(["DRIVER_ASSIGNED"]);
const FILTERS = [
  { key: "ALL", label: "common.all" },
  { key: "ACTIVE", label: "provider.statusActive" },
  { key: "UPCOMING", label: "provider.statusUpcoming" },
  { key: "COMPLETED", label: "provider.statusCompleted" },
  { key: "CANCELLED", label: "provider.statusCancelled" },
  { key: "DISPUTED", label: "provider.statusDisputed" },
];

export default function ProviderTrips() {
  const { t } = useI18n();
  const [trips, setTrips] = useState(null);
  const [filter, setFilter] = useState("ALL");
  const [q, setQ] = useState("");
  useEffect(() => { api.get("/provider/trips").then(({ data }) => setTrips(data)).catch(() => setTrips([])); }, []);
  const filtered = useMemo(() => {
    let list = trips || [];
    if (filter === "ACTIVE") list = list.filter((t) => ACTIVE.has(t.status));
    else if (filter === "UPCOMING") list = list.filter((t) => UPCOMING.has(t.status));
    else if (filter === "COMPLETED") list = list.filter((t) => t.status === "COMPLETED");
    else if (filter === "CANCELLED") list = list.filter((t) => t.status === "CANCELLED");
    else if (filter === "DISPUTED") list = list.filter((t) => t.status === "DISPUTED");
    const ql = q.trim().toLowerCase();
    if (ql) list = list.filter((t) => (t.shipment_title || "").toLowerCase().includes(ql) || (t.driver_name || "").toLowerCase().includes(ql));
    return list;
  }, [trips, filter, q]);
  if (trips === null) return <Spinner label={t("common.loading")} />;
  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={t("provider.trips")} />
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-4">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button key={f.key} data-testid={`trips-filter-${f.key}`} onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-lg text-sm font-semibold border ${filter === f.key ? "bg-[#16233A] text-white border-[#16233A]" : "bg-white text-slate-600 border-slate-200 hover:border-[#F1701E]"}`}>
              {t(f.label)}
            </button>
          ))}
        </div>
        <div className="md:w-64"><Input data-testid="trips-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("provider.searchPh")} /></div>
      </div>
      {filtered.length === 0 ? <Card><EmptyState icon={Truck} title={t("common.none")} /></Card> : (
        <div className="grid gap-3">
          {filtered.map((tr) => (
            <Link key={tr.id} to={`/provider/trips/${tr.id}`}>
              <Card data-testid={`provider-trip-${tr.id}`} className="hover:border-[#F1701E] transition-colors min-w-0 overflow-hidden">
                <div className="flex items-center justify-between gap-3 mb-2 min-w-0">
                  <h3 className="font-bold text-[#16233A] truncate">{tr.shipment_title || tr.id}</h3>
                  <StatusBadge status={tr.status} />
                </div>
                <RouteInline pickup={tr.pickup_location} delivery={tr.delivery_location} />
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3 text-xs text-slate-500">
                  <div>{t("shipment.driver") || t("nav.drivers")}: <b className="text-slate-700">{tr.driver_name || "\u2014"}</b></div>
                  <div>{t("provider.amount")}: <b className="text-slate-700">{tr.price} {t("common.currency")}</b></div>
                  <div>{t("provider.paymentStatus")}: <b className="text-slate-700">{tr.payment_status || "\u2014"}</b></div>
                  <div>{t("provider.podStatus")}: <b className="text-slate-700">{tr.delivery_confirmation ? t("common.yes") : t("common.no")}</b></div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
