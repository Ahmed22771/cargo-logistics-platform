import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Star, Truck, CheckCircle2, Package, Info, Trash2 } from "lucide-react";
import { Card, Btn, Spinner, Field, Textarea, Input } from "../../components/ui-kit";
import { StatusBadge, VerificationBadge } from "../../components/StatusBadge";
import { RouteDisplay } from "../../components/RouteDisplay";
import { StaticRouteMap } from "../../components/MapPicker";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const TRACK_STEPS = ["DRIVER_ASSIGNED", "DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED", "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION", "DELIVERED_PENDING_CONFIRMATION"];

function Stars({ value, onChange, testId }) {
  return (
    <div className="flex gap-1" data-testid={testId}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" onClick={() => onChange(n)} data-testid={`${testId}-${n}`}>
          <Star className={`w-6 h-6 ${n <= value ? "fill-[#F1701E] text-[#F1701E]" : "text-slate-300"}`} />
        </button>
      ))}
    </div>
  );
}

export default function ShipmentDetail() {
  const { id } = useParams();
  const { t, isRTL } = useI18n();
  const navigate = useNavigate();
  const [shipment, setShipment] = useState(null);
  const [bids, setBids] = useState([]);
  const [trip, setTrip] = useState(null);
  const [busy, setBusy] = useState(false);
  const [rating, setRating] = useState({ overall: 5, service_quality: 5, communication: 5, on_time: 5, comment: "" });

  const load = useCallback(async () => {
    try {
      const { data: s } = await api.get(`/shipments/${id}`);
      setShipment(s);
      const { data: b } = await api.get(`/shipments/${id}/bids`);
      setBids(b);
      if (s.trip_id) { const { data: tr } = await api.get(`/trips/${s.trip_id}`); setTrip(tr); }
    } catch (e) { toast.error(apiErr(e)); }
  }, [id]);

  useEffect(() => { load(); const i = setInterval(load, 12000); return () => clearInterval(i); }, [load]);

  if (!shipment) return <Spinner label={t("common.loading")} />;

  const acceptBid = async (bid) => {
    setBusy(true);
    try { await api.post(`/bids/${bid.id}/accept`); toast.success(t("bid.accepted")); await load(); }
    catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  const confirmDelivery = async () => {
    setBusy(true);
    try { await api.post(`/trips/${trip.id}/confirm-delivery`, { reference: "" }); toast.success(t("common.success")); await load(); }
    catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  const submitRating = async () => {
    setBusy(true);
    try { await api.post(`/trips/${trip.id}/review`, rating); toast.success(t("rating.thanks")); await load(); }
    catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  const cancelShipment = async () => {
    setBusy(true);
    try { await api.delete(`/shipments/${id}`); toast.success(t("common.success")); navigate("/customer/shipments"); }
    catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  const currentIdx = trip ? TRACK_STEPS.indexOf(trip.status) : -1;
  const showBids = ["PUBLISHED", "BIDDING"].includes(shipment.status);
  const showTrip = !!trip;
  const canConfirm = trip && trip.status === "DELIVERED_PENDING_CONFIRMATION";
  const canRate = trip && trip.customer_confirmed && trip.status !== "COMPLETED";

  return (
    <div className="max-w-3xl mx-auto">
      <button onClick={() => navigate("/customer/shipments")} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4" data-testid="detail-back-btn">
        <ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} /> {t("nav.myShipments")}
      </button>

      <Card className="mb-4">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div><h1 className="text-xl font-extrabold text-[#16233A]">{shipment.title}</h1>
            <p className="text-sm text-slate-400 mt-1">{shipment.description}</p></div>
          <StatusBadge status={shipment.status} />
        </div>
        <StaticRouteMap pickup={shipment.pickup_location} delivery={shipment.delivery_location} height={220} />
        <div className="mt-4"><RouteDisplay pickup={shipment.pickup_location} delivery={shipment.delivery_location} /></div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 text-sm">
          {[[t("shipment.category"), shipment.category], [t("shipment.weight"), shipment.weight], [t("shipment.vehicleType"), t(`shipment.vehicle${(shipment.vehicle_type||"flatbed").charAt(0).toUpperCase()+(shipment.vehicle_type||"flatbed").slice(1)}`)], [t("shipment.expectedPrice"), shipment.expected_price ? `${shipment.expected_price} ${t("common.currency")}` : "—"]].map(([l, v], i) => (
            <div key={i} className="bg-slate-50 rounded-lg p-2.5"><div className="text-xs text-slate-400">{l}</div><div className="font-semibold text-slate-700">{v || "—"}</div></div>
          ))}
        </div>
        {["DRAFT", "PUBLISHED", "BIDDING"].includes(shipment.status) && (
          <Btn variant="ghost" onClick={cancelShipment} disabled={busy} data-testid="cancel-shipment-btn" className="mt-4 text-red-600 hover:bg-red-50"><Trash2 className="w-4 h-4" /> {t("common.cancel")}</Btn>
        )}
      </Card>

      {/* Bids */}
      {showBids && (
        <Card className="mb-4">
          <h2 className="font-bold text-lg text-[#16233A] mb-4 flex items-center gap-2"><Package className="w-5 h-5 text-[#F1701E]" /> {t("bid.compare")} ({bids.length})</h2>
          {bids.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-6">{t("shipment.noBidsYet")}</p>
          ) : (
            <div className="space-y-3">
              {bids.map((b) => (
                <div key={b.id} data-testid={`bid-${b.id}`} className="border border-slate-200 rounded-xl p-4 hover:border-[#F1701E]/40 transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[#16233A]">{b.driver_name}</span>
                        <VerificationBadge status={b.driver_verification} />
                      </div>
                      <div className="flex items-center gap-4 text-xs text-slate-500 mt-1.5">
                        <span className="flex items-center gap-1"><Star className="w-3.5 h-3.5 fill-[#F1701E] text-[#F1701E]" /> {b.driver_rating || 0} ({b.driver_rating_count || 0})</span>
                        <span className="flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> {b.driver_completed_trips || 0} {t("bid.completedTrips")}</span>
                        <span className="flex items-center gap-1"><Truck className="w-3.5 h-3.5" /> {b.driver_vehicle?.type || "—"}</span>
                      </div>
                      {b.note && <p className="text-sm text-slate-600 mt-2 bg-slate-50 rounded-lg p-2">{b.note}</p>}
                    </div>
                    <div className="text-end shrink-0">
                      <div className="text-xl font-extrabold text-[#F1701E]">{b.price}</div>
                      <div className="text-xs text-slate-400">{t("common.currency")}</div>
                    </div>
                  </div>
                  {shipment.status !== "DRAFT" && !shipment.accepted_bid_id && b.status === "PENDING" && (
                    <Btn variant="accent" onClick={() => acceptBid(b)} disabled={busy} data-testid={`accept-bid-${b.id}`} className="w-full mt-3"><CheckCircle2 className="w-4 h-4" /> {t("bid.accept")}</Btn>
                  )}
                  {b.status === "ACCEPTED" && <div className="mt-3 text-sm font-semibold text-emerald-600 flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4" /> {t("bid.won")}</div>}
                  {b.status === "REJECTED" && <div className="mt-3 text-sm text-slate-400">{t("bid.lost")}</div>}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Trip tracking */}
      {showTrip && (
        <Card className="mb-4">
          <h2 className="font-bold text-lg text-[#16233A] mb-1 flex items-center gap-2"><Truck className="w-5 h-5 text-[#F1701E]" /> {t("trip.tracking")}</h2>
          <p className="text-sm text-slate-400 mb-4">{t("bid.driver")}: <span className="font-semibold text-slate-600">{trip.driver_name}</span></p>
          <div className="space-y-1">
            {TRACK_STEPS.map((s, i) => (
              <div key={s} className="flex items-center gap-3" data-testid={`track-${s}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${i <= currentIdx ? "bg-[#F1701E] text-white" : "bg-slate-100 text-slate-300"}`}>
                  {i < currentIdx ? <CheckCircle2 className="w-4 h-4" /> : <div className="w-2 h-2 rounded-full bg-current" />}
                </div>
                <span className={`text-sm ${i === currentIdx ? "font-bold text-[#16233A]" : i < currentIdx ? "text-slate-600" : "text-slate-400"}`}>{t(`status.${s}`)}</span>
              </div>
            ))}
          </div>
          {canConfirm && <Btn variant="accent" onClick={confirmDelivery} disabled={busy} data-testid="confirm-delivery-btn" className="w-full mt-5"><CheckCircle2 className="w-4 h-4" /> {t("shipment.confirmDeliveryBtn")}</Btn>}
        </Card>
      )}

      {/* Rating */}
      {canRate && (
        <Card>
          <h2 className="font-bold text-lg text-[#16233A] mb-4 flex items-center gap-2"><Star className="w-5 h-5 text-[#F1701E]" /> {t("shipment.rateDriver")}</h2>
          <div className="space-y-4">
            {[["overall", t("rating.overall")], ["service_quality", t("rating.serviceQuality")], ["communication", t("rating.communication")], ["on_time", t("rating.onTime")]].map(([k, l]) => (
              <div key={k} className="flex items-center justify-between"><span className="text-sm text-slate-600">{l}</span><Stars value={rating[k]} onChange={(v) => setRating((r) => ({ ...r, [k]: v }))} testId={`rate-${k}`} /></div>
            ))}
            <Field label={t("rating.comment")}><Textarea rows={2} data-testid="rate-comment" value={rating.comment} onChange={(e) => setRating((r) => ({ ...r, comment: e.target.value }))} /></Field>
            <Btn variant="accent" onClick={submitRating} disabled={busy} data-testid="submit-rating-btn" className="w-full">{t("rating.submit")}</Btn>
          </div>
        </Card>
      )}

      {trip && trip.status === "COMPLETED" && (
        <Card><div className="flex items-center gap-2 text-emerald-600 font-semibold"><CheckCircle2 className="w-5 h-5" /> {t("status.COMPLETED")}</div></Card>
      )}
    </div>
  );
}
