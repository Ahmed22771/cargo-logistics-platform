import React, { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { Truck, CheckCircle2, ArrowRight } from "lucide-react";
import { Card, Spinner, PageHeader, EmptyState, Btn } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteDisplay } from "../../components/RouteDisplay";
import { StaticRouteMap } from "../../components/MapPicker";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const FLOW = ["DRIVER_ASSIGNED", "DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED", "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION", "DELIVERED_PENDING_CONFIRMATION"];

export default function ActiveTrip() {
  const { t, isRTL } = useI18n();
  const [trip, setTrip] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/trips/mine");
      const active = data.find((tr) => !["COMPLETED", "CANCELLED", "DELIVERED"].includes(tr.status)) || data.find((tr) => tr.status === "DELIVERED");
      setTrip(active || null);
    } catch {} finally { setLoaded(true); }
  }, []);
  useEffect(() => { load(); const i = setInterval(load, 12000); return () => clearInterval(i); }, [load]);

  if (!loaded) return <Spinner label={t("common.loading")} />;
  if (!trip) return <div><PageHeader title={t("trip.active")} /><Card><EmptyState icon={Truck} title={t("trip.noActive")} /></Card></div>;

  const idx = FLOW.indexOf(trip.status);
  const nextStatus = idx >= 0 && idx < FLOW.length - 1 ? FLOW[idx + 1] : null;

  const updateStatus = async () => {
    if (!nextStatus) return;
    setBusy(true);
    try {
      const loc = trip.delivery_location;
      await api.post(`/trips/${trip.id}/status`, { status: nextStatus, lat: loc?.lat, lng: loc?.lng });
      toast.success(t("common.success")); await load();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  return (
    <div className="max-w-2xl">
      <PageHeader title={t("trip.active")} action={<StatusBadge status={trip.status} />} />
      <Card className="mb-4">
        <h3 className="font-bold text-[#16233A] mb-1">{trip.shipment_title}</h3>
        <p className="text-sm text-slate-400 mb-3">{t("trip.customer")}: {trip.customer_name}</p>
        <StaticRouteMap pickup={trip.pickup_location} delivery={trip.delivery_location} height={220} />
        <div className="mt-4"><RouteDisplay pickup={trip.pickup_location} delivery={trip.delivery_location} /></div>
        <div className="mt-3 text-sm text-slate-500">{t("common.price")}: <span className="font-bold text-[#F1701E]">{trip.price} {t("common.currency")}</span></div>
      </Card>

      <Card>
        <h3 className="font-bold text-[#16233A] mb-4">{t("trip.progress")}</h3>
        <div className="space-y-1 mb-5">
          {FLOW.map((s, i) => (
            <div key={s} className="flex items-center gap-3" data-testid={`trip-step-${s}`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${i <= idx ? "bg-[#F1701E] text-white" : "bg-slate-100 text-slate-300"}`}>
                {i < idx ? <CheckCircle2 className="w-4 h-4" /> : <div className="w-2 h-2 rounded-full bg-current" />}
              </div>
              <span className={`text-sm ${i === idx ? "font-bold text-[#16233A]" : i < idx ? "text-slate-600" : "text-slate-400"}`}>{t(`status.${s}`)}</span>
            </div>
          ))}
        </div>
        {nextStatus ? (
          <Btn variant="accent" onClick={updateStatus} disabled={busy} data-testid="update-status-btn" className="w-full">
            {t("trip.updateStatus")}: {t(`status.${nextStatus}`)} <ArrowRight className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
          </Btn>
        ) : trip.status === "DELIVERED_PENDING_CONFIRMATION" ? (
          <div className="text-center text-sm text-slate-500 bg-slate-50 rounded-lg p-3">{t("status.DELIVERED_PENDING_CONFIRMATION")}</div>
        ) : (
          <div className="text-center text-sm text-emerald-600 font-semibold flex items-center justify-center gap-1.5"><CheckCircle2 className="w-4 h-4" /> {t("trip.confirmedDelivery")}</div>
        )}
      </Card>
    </div>
  );
}
