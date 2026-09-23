import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Package, Truck, Gavel } from "lucide-react";
import { Card, Spinner, PageHeader, EmptyState, Btn, Field, Input, Textarea } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteDisplay } from "../../components/RouteDisplay";
import { VerificationBanner } from "./VerificationBanner";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api, { apiErr, eligibilityError } from "../../lib/api";

function BidModal({ shipment, onClose, onSubmitted }) {
  const { t } = useI18n();
  const [price, setPrice] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (busy) return; // prevent double-submit
    const p = parseFloat(price);
    if (!p || p <= 0) { toast.error(t("bid.priceRequired")); return; }
    setBusy(true);
    try { await api.post(`/shipments/${shipment.id}/bids`, { price: p, note }); toast.success(t("bid.submitted")); onSubmitted(); }
    catch (e) {
      const elig = eligibilityError(e);
      if (elig) {
        const detail = (elig.reasons || [])
          .map((r) => t(`bid.eligibilityReasons.${r?.code}`, r?.message || ""))
          .filter(Boolean)
          .join(" • ");
        toast.error(detail ? `${t("bid.notEligible")}: ${detail}` : t("bid.notEligible"));
      } else {
        toast.error(apiErr(e));
      }
    } finally { setBusy(false); }
  };
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="bid-modal"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="absolute inset-0 bg-black/50"
        data-testid="bid-modal-overlay"
        onClick={onClose}
      />
      <div
        className="relative bg-white w-full max-w-md rounded-2xl shadow-xl max-h-[85vh] flex flex-col animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 pb-3 shrink-0">
          <h2 className="font-bold text-lg text-[#16233A] mb-1">{t("bid.submit")}</h2>
          <p className="text-sm text-slate-400 line-clamp-2">{shipment.title}</p>
        </div>
        <div className="px-6 overflow-y-auto flex-1">
          <div className="space-y-4">
            <Field label={t("bid.price")} required hint={t("bid.enterPrice")}>
              <Input type="number" data-testid="bid-price-input" value={price} onChange={(e) => setPrice(e.target.value)} className="force-ltr" placeholder="0.000" />
            </Field>
            <Field label={t("bid.note")}><Textarea rows={2} data-testid="bid-note-input" value={note} onChange={(e) => setNote(e.target.value)} /></Field>
          </div>
        </div>
        <div className="p-6 pt-3 shrink-0 border-t border-slate-100 flex gap-2">
          <Btn variant="secondary" onClick={onClose} disabled={busy} data-testid="cancel-bid-btn" className="flex-1 justify-center">{t("common.cancel")}</Btn>
          <Btn variant="accent" onClick={submit} disabled={busy} data-testid="submit-bid-btn" className="flex-1 justify-center"><Gavel className="w-4 h-4" /> {t("bid.submit")}</Btn>
        </div>
      </div>
    </div>
  );
}

export default function AvailableShipments() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [shipments, setShipments] = useState(null);
  const [modal, setModal] = useState(null);
  const approved = user?.verification_status === "APPROVED";

  const load = () => {
    if (!approved) { setShipments([]); return; }
    api.get("/marketplace/shipments").then(({ data }) => setShipments(data)).catch(() => setShipments([]));
  };
  useEffect(load, [approved]);

  if (shipments === null) return <Spinner label={t("common.loading")} />;

  return (
    <div>
      <PageHeader title={t("nav.availableShipments")} />
      <VerificationBanner />
      {!approved ? null : shipments.length === 0 ? (
        <Card><EmptyState icon={Package} title={t("shipment.noShipments")} /></Card>
      ) : (
        <div className="grid gap-3">
          {shipments.map((s) => (
            <Card key={s.id} data-testid={`available-${s.id}`}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div><h3 className="font-bold text-[#16233A]">{s.title}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">{s.category} · {s.weight} kg · {t(`shipment.vehicle${(s.vehicle_type||"flatbed").charAt(0).toUpperCase()+(s.vehicle_type||"flatbed").slice(1)}`)}</p></div>
                <StatusBadge status={s.status} />
              </div>
              <RouteDisplay pickup={s.pickup_location} delivery={s.delivery_location} />
              {s.expected_price && <div className="text-sm text-slate-500 mt-3">{t("shipment.expectedPrice")}: <span className="font-bold text-[#F1701E]">{s.expected_price} {t("common.currency")}</span></div>}
              <div className="mt-4">
                {s.already_bid ? (
                  <div className="text-sm font-semibold text-emerald-600 flex items-center gap-1.5"><Gavel className="w-4 h-4" /> {t("bid.alreadyBid")}</div>
                ) : (
                  <Btn variant="accent" data-testid={`bid-btn-${s.id}`} onClick={() => setModal(s)} className="w-full sm:w-auto"><Gavel className="w-4 h-4" /> {t("bid.submit")}</Btn>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
      {modal && <BidModal shipment={modal} onClose={() => setModal(null)} onSubmitted={() => { setModal(null); load(); }} />}
    </div>
  );
}
