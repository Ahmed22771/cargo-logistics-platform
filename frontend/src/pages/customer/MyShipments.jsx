import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Package, Plus, AlertCircle, ShieldCheck, CreditCard } from "lucide-react";
import { Card, Btn, Spinner, PageHeader, EmptyState } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function MyShipments() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [shipments, setShipments] = useState(null);
  const [trips, setTrips] = useState([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [{ data: s }, { data: tr }] = await Promise.all([
          api.get("/shipments/mine"),
          api.get("/trips/mine"),
        ]);
        if (!cancelled) {
          setShipments(s);
          setTrips(tr || []);
        }
      } catch {
        if (!cancelled) {
          setShipments([]);
          setTrips([]);
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (shipments === null) return <Spinner label={t("common.loading")} />;

  const tripByShipment = trips.reduce((acc, tr) => {
    acc[tr.shipment_id] = tr;
    return acc;
  }, {});

  const pendingConfirm = shipments.filter((s) => s.status === "DELIVERED_PENDING_CONFIRMATION");
  const needsPayment = shipments.filter((s) => {
    const tr = tripByShipment[s.id];
    return tr && tr.status === "DRIVER_ASSIGNED" && (tr.payment_status || "NONE") !== "HELD";
  });

  const hasAction = pendingConfirm.length > 0 || needsPayment.length > 0;

  return (
    <div className="min-w-0">
      <PageHeader title={t("nav.myShipments")}
        action={<Btn variant="accent" data-testid="create-shipment-btn" onClick={() => navigate("/customer/create")}><Plus className="w-4 h-4" /> {t("shipment.create")}</Btn>} />

      {hasAction && (
        <Card
          className="mb-4 border-orange-200 bg-gradient-to-br from-orange-50 to-amber-50"
          data-testid="action-required-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-[#F1701E] flex items-center justify-center shrink-0">
              <AlertCircle className="w-4 h-4 text-white" />
            </div>
            <h3 className="font-bold text-[#16233A]">{t("action.needsAction")}</h3>
          </div>
          <div className="space-y-2">
            {pendingConfirm.map((s) => (
              <div
                key={`pod-${s.id}`}
                data-testid={`action-pod-${s.id}`}
                className="flex flex-col sm:flex-row sm:items-center gap-2 rounded-xl bg-white border border-orange-200 p-3 overflow-hidden"
              >
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm text-[#16233A] truncate">{t("action.podPending")}</div>
                    <div className="text-xs text-slate-500 truncate">{s.title}</div>
                  </div>
                </div>
                <Btn
                  variant="accent"
                  onClick={() => navigate(`/customer/shipment/${s.id}`)}
                  data-testid={`review-pod-btn-${s.id}`}
                  className="shrink-0 w-full sm:w-auto"
                >
                  {t("action.reviewPod")}
                </Btn>
              </div>
            ))}
            {needsPayment.map((s) => {
              const tr = tripByShipment[s.id];
              return (
                <div
                  key={`pay-${s.id}`}
                  data-testid={`action-pay-${s.id}`}
                  className="flex flex-col sm:flex-row sm:items-center gap-2 rounded-xl bg-white border border-orange-200 p-3 overflow-hidden"
                >
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <CreditCard className="w-5 h-5 text-[#F1701E] shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-sm text-[#16233A] truncate">{t("action.needsPayment")}</div>
                      <div className="text-xs text-slate-500 truncate">
                        {s.title} · {Number(tr.price || 0).toFixed(3)} {t("common.currency")}
                      </div>
                    </div>
                  </div>
                  <Btn
                    variant="accent"
                    onClick={() => navigate(`/customer/pay/${tr.id}`)}
                    data-testid={`complete-payment-btn-${s.id}`}
                    className="shrink-0 w-full sm:w-auto"
                  >
                    {t("pay.completePayment")}
                  </Btn>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {shipments.length === 0 ? (
        <Card><EmptyState icon={Package} title={t("shipment.noShipments")} subtitle={t("shipment.createFirst")}
          action={<Btn variant="accent" onClick={() => navigate("/customer/create")}><Plus className="w-4 h-4" /> {t("shipment.create")}</Btn>} /></Card>
      ) : (
        <div className="grid gap-3">
          {shipments.map((s) => (
            <Card key={s.id} data-testid={`shipment-card-${s.id}`} className="cursor-pointer hover:shadow-md transition-shadow min-w-0 overflow-hidden" onClick={() => navigate(`/customer/shipment/${s.id}`)}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0">
                  <h3 className="font-bold text-[#16233A] truncate">{s.title}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">{s.category} · {s.weight} {t("common.km") === "km" ? "kg" : "كجم"}</p>
                </div>
                <StatusBadge status={s.status} />
              </div>
              <RouteInline pickup={s.pickup_location} delivery={s.delivery_location} />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
