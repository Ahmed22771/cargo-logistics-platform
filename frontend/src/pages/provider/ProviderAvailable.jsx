import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Package, Search, Gavel, X, AlertCircle } from "lucide-react";
import { Card, Btn, Field, Input, Textarea, Spinner, EmptyState, PageHeader } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

function BidModal({ shipment, drivers, onClose, onSubmitted }) {
  const { t } = useI18n();
  const [driverId, setDriverId] = useState(drivers[0]?.id || "");
  const [price, setPrice] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (busy) return;
    if (!driverId) return toast.error(t("provider.noApprovedDrivers"));
    const p = parseFloat(price);
    if (!p || p <= 0) return toast.error(t("pay.priceInvalid"));
    setBusy(true);
    try {
      await api.post(`/provider/shipments/${shipment.id}/bids`, { driver_id: driverId, price: p, note });
      toast.success(t("common.success"));
      onSubmitted && onSubmitted();
      onClose();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="provider-bid-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-[#16233A]">{t("provider.submitBid")}</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-500" /></button>
        </div>
        <div className="text-sm text-slate-500 mb-4 truncate">{shipment.title}</div>
        {drivers.length === 0 ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" /><span>{t("provider.linkDriverFirst")}</span>
          </div>
        ) : (
          <div className="space-y-4">
            <Field label={t("provider.chooseDriver")} required>
              <select data-testid="bid-driver-select" value={driverId} onChange={(e) => setDriverId(e.target.value)}
                className="w-full bg-white text-slate-800 border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#F1701E]">
                {drivers.map((d) => <option key={d.id} value={d.id}>{d.name || d.phone}</option>)}
              </select>
            </Field>
            <Field label={t("provider.bidPrice")} required>
              <Input type="number" min="0" step="0.001" data-testid="bid-price-input" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="0.000" className="force-ltr" />
            </Field>
            <Field label={t("provider.bidNote")}>
              <Textarea rows={2} data-testid="bid-note-input" value={note} onChange={(e) => setNote(e.target.value)} />
            </Field>
            <div className="flex gap-2">
              <Btn variant="secondary" onClick={onClose} disabled={busy} className="flex-1 justify-center">{t("common.cancel")}</Btn>
              <Btn variant="accent" onClick={submit} disabled={busy} data-testid="submit-provider-bid-btn" className="flex-1 justify-center"><Gavel className="w-4 h-4" /> {t("bid.submit") || t("provider.submitBid")}</Btn>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ProviderAvailable() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [shipments, setShipments] = useState([]);
  const [bids, setBids] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [q, setQ] = useState("");
  const [modal, setModal] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [{ data: opps }, { data: myBids }, { data: drs }] = await Promise.all([
        api.get("/provider/opportunities"),
        api.get("/provider/bids"),
        api.get("/provider/drivers"),
      ]);
      setShipments(opps);
      setBids(myBids);
      setDrivers((drs || []).filter((d) => d.verification_status === "APPROVED" && (d.status || "active").toLowerCase() !== "disabled"));
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const bidShipmentIds = useMemo(() => new Set(bids.filter((b) => b.status === "PENDING" || b.status === "ACCEPTED").map((b) => b.shipment_id)), [bids]);
  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    if (!ql) return shipments;
    return shipments.filter((s) => (s.title || "").toLowerCase().includes(ql) || (s.category || "").toLowerCase().includes(ql));
  }, [q, shipments]);

  if (loading) return <Spinner label={t("common.loading")} />;

  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={t("provider.availableShipments")} />
      <div className="mb-4 relative">
        <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
        <Input data-testid="available-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("provider.searchPh")} className="ps-9" />
      </div>
      {filtered.length === 0 ? <Card><EmptyState icon={Package} title={t("shipment.noShipments")} /></Card> : (
        <div className="grid gap-3 min-w-0">
          {filtered.map((s) => {
            const alreadyBid = bidShipmentIds.has(s.id);
            return (
              <Card key={s.id} data-testid={`prov-avail-${s.id}`} className="min-w-0 overflow-hidden">
                <div className="flex items-center justify-between gap-3 mb-2 min-w-0">
                  <h3 className="min-w-0 truncate font-bold text-[#16233A]">{s.title}</h3>
                  <StatusBadge status={s.status} />
                </div>
                {s.description && <p className="text-sm text-slate-500 mb-2 line-clamp-2">{s.description}</p>}
                <RouteInline pickup={s.pickup_location} delivery={s.delivery_location} />
                <div className="flex flex-wrap gap-2 mt-3 text-xs text-slate-500">
                  {s.pickup_date && <span>{t("common.date")}: {s.pickup_date}</span>}
                  {s.vehicle_type && <span>{t("provider.vehicleType")}: {s.vehicle_type}</span>}
                  {s.expected_price && <span>{t("common.price")}: {s.expected_price} {t("common.currency")}</span>}
                </div>
                <div className="mt-3">
                  {alreadyBid ? (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 rounded-full px-3 py-1">{t("provider.bids")}: {t("common.yes")}</span>
                  ) : (
                    <Btn variant="accent" data-testid={`open-bid-${s.id}`} onClick={() => setModal(s)}><Gavel className="w-4 h-4" /> {t("provider.submitBid")}</Btn>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
      {modal && <BidModal shipment={modal} drivers={drivers} onClose={() => setModal(null)} onSubmitted={load} />}
    </div>
  );
}
