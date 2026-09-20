import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Truck, User, MapPin, Wallet, ShieldCheck } from "lucide-react";
import { Card, Spinner, PageHeader } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteDisplay } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function ProviderTripDetail() {
  const { id } = useParams();
  const { t } = useI18n();
  const [trip, setTrip] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.get(`/trips/${id}`).then(({ data }) => setTrip(data)).catch((e) => setError(e?.response?.data?.detail || "error")); }, [id]);
  if (error) return <div className="text-center text-slate-500"><p>{error}</p><Link to="/provider/trips" className="text-[#F1701E] font-semibold">{t("common.back")}</Link></div>;
  if (!trip) return <Spinner label={t("common.loading")} />;
  return (
    <div className="min-w-0 overflow-x-hidden">
      <Link to="/provider/trips" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"><ArrowLeft className="w-4 h-4" /> {t("common.back")}</Link>
      <PageHeader title={trip.shipment_title || t("provider.trips")} action={<StatusBadge status={trip.status} />} />
      <div className="grid gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-3"><MapPin className="w-4 h-4 text-[#F1701E]" /><h3 className="font-bold text-[#16233A]">{t("provider.route")}</h3></div>
          <RouteDisplay pickup={trip.pickup_location} delivery={trip.delivery_location} />
        </Card>
        <Card>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><div className="text-slate-400">{t("shipment.driver") || t("nav.drivers")}</div><div className="font-semibold text-[#16233A]">{trip.driver_name || "\u2014"}</div></div>
            <div><div className="text-slate-400">{t("provider.amount")}</div><div className="font-semibold text-[#16233A]">{trip.price} {t("common.currency")}</div></div>
            <div><div className="text-slate-400">{t("provider.paymentStatus")}</div><div className="font-semibold text-[#16233A]">{trip.payment_status || "\u2014"}</div></div>
            <div><div className="text-slate-400">{t("provider.podStatus")}</div><div className="font-semibold text-[#16233A]">{trip.delivery_confirmation ? t("common.yes") : t("common.no")}</div></div>
            {trip.vehicle?.plate_number && <div><div className="text-slate-400">{t("provider.plateNumber")}</div><div className="font-semibold text-[#16233A] force-ltr">{trip.vehicle.plate_number}</div></div>}
          </div>
        </Card>
        {trip.delivery_confirmation && (
          <Card>
            <div className="flex items-center gap-2 mb-3"><ShieldCheck className="w-4 h-4 text-emerald-600" /><h3 className="font-bold text-[#16233A]">{t("p5.pod.title")}</h3></div>
            {trip.delivery_confirmation.pod_photo && <img alt="POD" src={trip.delivery_confirmation.pod_photo} className="w-full max-w-md rounded-lg mb-3" />}
            {trip.delivery_confirmation.pod_notes && <p className="text-sm text-slate-600">{trip.delivery_confirmation.pod_notes}</p>}
          </Card>
        )}
        {trip.tracking_events?.length > 0 && (
          <Card>
            <h3 className="font-bold text-[#16233A] mb-3">{t("nav.tracking")}</h3>
            <div className="space-y-2">
              {trip.tracking_events.map((ev) => (
                <div key={ev.id} className="flex items-center justify-between text-sm border-b border-slate-100 py-1.5">
                  <span className="font-semibold text-slate-700">{t(`status.${ev.status}`) || ev.status}</span>
                  <span className="text-xs text-slate-400">{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ""}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
