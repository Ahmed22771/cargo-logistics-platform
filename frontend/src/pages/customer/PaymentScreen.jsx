import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, CreditCard, Info, Lock, User } from "lucide-react";
import { Card, Btn, Spinner } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

export default function PaymentScreen() {
  const { tripId } = useParams();
  const { t, isRTL } = useI18n();
  const navigate = useNavigate();
  const [trip, setTrip] = useState(null);
  const [error, setError] = useState("");
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/trips/${tripId}`);
        if (!cancelled) setTrip(data);
      } catch (e) {
        if (!cancelled) setError(apiErr(e) || t("pay.loadFailed"));
      }
    })();
    return () => { cancelled = true; };
  }, [tripId, t]);

  const goToShipment = (sid) => navigate(`/customer/shipment/${sid}`);

  const pay = async () => {
    if (paying) return;
    setPaying(true);
    try {
      const { data } = await api.post(`/trips/${tripId}/pay`);
      const updated = data?.trip || null;
      if (updated) setTrip(updated);
      if (data?.already_paid) {
        toast.success(t("pay.alreadyPaid"));
      } else {
        toast.success(t("pay.success"));
      }
      const sid = updated?.shipment_id || trip?.shipment_id;
      if (sid) goToShipment(sid);
    } catch (e) {
      toast.error(apiErr(e));
    } finally {
      setPaying(false);
    }
  };

  if (error) {
    return (
      <div className="max-w-lg mx-auto">
        <Card>
          <p className="text-red-600 font-semibold" data-testid="pay-error">{error}</p>
          <Btn variant="secondary" onClick={() => navigate("/customer/shipments")} className="mt-4">
            <ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} /> {t("nav.myShipments")}
          </Btn>
        </Card>
      </div>
    );
  }

  if (!trip) return <Spinner label={t("common.loading")} />;

  const alreadyPaid = trip.payment_status === "HELD";
  const price = Number(trip.price || 0);

  return (
    <div className="max-w-lg mx-auto pb-8">
      <button
        onClick={() => trip.shipment_id ? goToShipment(trip.shipment_id) : navigate("/customer/shipments")}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"
        data-testid="pay-back-btn"
      >
        <ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} /> {t("common.back")}
      </button>

      <Card data-testid="pay-card">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center">
            <CreditCard className="w-5 h-5 text-[#F1701E]" />
          </div>
          <div>
            <h1 className="font-extrabold text-lg text-[#16233A]">{t("pay.title")}</h1>
            <p className="text-xs text-slate-400">{t("pay.subtitle")}</p>
          </div>
        </div>

        <div className="mt-4 space-y-2 text-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <span className="text-slate-500 flex items-center gap-1.5">
              <Info className="w-4 h-4" /> {t("pay.shipmentRef")}
            </span>
            <span className="font-semibold text-slate-700 force-ltr" data-testid="pay-shipment-ref">
              #{(trip.shipment_id || "").slice(0, 8).toUpperCase()}
            </span>
          </div>
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <span className="text-slate-500 flex items-center gap-1.5">
              <User className="w-4 h-4" /> {t("pay.driver")}
            </span>
            <span className="font-semibold text-slate-700" data-testid="pay-driver-name">
              {trip.driver_name || "—"}
            </span>
          </div>
          <div className="mt-2 rounded-xl bg-slate-50 p-4 flex items-center justify-between">
            <span className="text-sm text-slate-500">{t("pay.amount")}</span>
            <span className="font-extrabold text-2xl text-[#F1701E] force-ltr" data-testid="pay-amount">
              {price.toFixed(3)} <span className="text-sm font-semibold text-slate-500">{t("common.currency")}</span>
            </span>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2 text-xs text-slate-500 bg-amber-50 border border-amber-200 rounded-lg p-2.5">
          <Lock className="w-4 h-4 text-amber-600 shrink-0" />
          <span data-testid="pay-demo-badge">{t("pay.demoBadge")}</span>
        </div>

        {alreadyPaid ? (
          <div className="mt-5 space-y-2">
            <div
              className="w-full rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700 text-center"
              data-testid="pay-held-badge"
            >
              {t("pay.held")}
            </div>
            <Btn
              variant="primary"
              onClick={() => goToShipment(trip.shipment_id)}
              className="w-full justify-center"
              data-testid="pay-go-detail-btn"
            >
              {t("common.view")}
            </Btn>
          </div>
        ) : (
          <div className="mt-5 flex flex-col-reverse sm:flex-row gap-2">
            <Btn
              variant="secondary"
              onClick={() => trip.shipment_id ? goToShipment(trip.shipment_id) : navigate("/customer/shipments")}
              disabled={paying}
              data-testid="pay-cancel-btn"
              className="flex-1 justify-center"
            >
              {t("pay.cancel")}
            </Btn>
            <Btn
              variant="accent"
              onClick={pay}
              disabled={paying || price <= 0}
              data-testid="pay-now-btn"
              className="flex-1 justify-center"
            >
              <CreditCard className="w-4 h-4" /> {t("pay.payNow")}
            </Btn>
          </div>
        )}
      </Card>
    </div>
  );
}
