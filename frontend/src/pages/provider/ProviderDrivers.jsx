import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Users, Plus, Trash2, X, Phone } from "lucide-react";
import { Card, Btn, Field, Input, Spinner, EmptyState, PageHeader } from "../../components/ui-kit";
import { VerificationBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

function LinkModal({ onClose, onLinked }) {
  const { t } = useI18n();
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!phone.trim()) return toast.error(t("common.required"));
    setBusy(true);
    try {
      await api.post("/provider/drivers/link", { phone: phone.trim() });
      toast.success(t("provider.linkedSuccess"));
      onLinked && onLinked();
      onClose();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="link-driver-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-[#16233A]">{t("provider.addDriver")}</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-500" /></button>
        </div>
        <p className="text-sm text-slate-500 mb-4">{t("provider.linkExplain")}</p>
        <Field label={t("provider.linkDriverPhone")} required>
          <div className="relative">
            <Phone className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
            <Input data-testid="link-driver-phone" value={phone} onChange={(e) => setPhone(e.target.value)} className="ps-9 force-ltr" placeholder="+96890000002" />
          </div>
        </Field>
        <div className="flex gap-2 mt-4">
          <Btn variant="secondary" onClick={onClose} disabled={busy} className="flex-1 justify-center">{t("common.cancel")}</Btn>
          <Btn variant="accent" onClick={submit} disabled={busy} data-testid="submit-link-driver" className="flex-1 justify-center">{t("common.submit")}</Btn>
        </div>
      </div>
    </div>
  );
}

export default function ProviderDrivers() {
  const { t } = useI18n();
  const [drivers, setDrivers] = useState(null);
  const [modal, setModal] = useState(false);
  const load = async () => {
    try { const { data } = await api.get("/provider/drivers"); setDrivers(data); }
    catch { setDrivers([]); }
  };
  useEffect(() => { load(); }, []);
  const unlink = async (d) => {
    if (!window.confirm(t("provider.confirmDelete"))) return;
    try { await api.delete(`/provider/drivers/${d.id}`); toast.success(t("common.success")); load(); }
    catch (e) { toast.error(apiErr(e)); }
  };
  if (drivers === null) return <Spinner label={t("common.loading")} />;
  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={t("provider.drivers")} action={<Btn variant="accent" data-testid="link-driver-btn" onClick={() => setModal(true)}><Plus className="w-4 h-4" /> {t("provider.addDriver")}</Btn>} />
      {drivers.length === 0 ? <Card><EmptyState icon={Users} title={t("provider.noApprovedDrivers")} subtitle={t("provider.linkDriverFirst")} /></Card> : (
        <div className="grid gap-3">
          {drivers.map((d) => (
            <Card key={d.id} data-testid={`driver-${d.id}`} className="min-w-0 overflow-hidden">
              <div className="flex items-center justify-between gap-3 mb-2 min-w-0">
                <Link to={`/provider/drivers/${d.id}`} className="font-bold text-[#16233A] truncate hover:text-[#F1701E]">{d.name || d.phone}</Link>
                <VerificationBadge status={d.verification_status || "DRAFT"} />
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
                <div>{t("provider.phone")}: <b className="text-slate-700 force-ltr">{d.phone}</b></div>
                <div>{t("common.status")}: <b className="text-slate-700">{d.status || "active"}</b></div>
                <div>{t("provider.vehicle") || t("nav.vehicle")}: <b className="text-slate-700 force-ltr">{d.current_vehicle?.plate_number || t("provider.unassigned")}</b></div>
                <div>{t("provider.tripHistory")}: <b className="text-slate-700">{d.active_trip ? t("provider.statusActive") : "\u2014"}</b></div>
              </div>
              <div className="mt-3 flex gap-2">
                <Btn variant="ghost" onClick={() => unlink(d)} data-testid={`unlink-driver-${d.id}`} className="text-red-600 hover:bg-red-50"><Trash2 className="w-4 h-4" /> {t("provider.unlinkDriver")}</Btn>
              </div>
            </Card>
          ))}
        </div>
      )}
      {modal && <LinkModal onClose={() => setModal(false)} onLinked={load} />}
    </div>
  );
}
