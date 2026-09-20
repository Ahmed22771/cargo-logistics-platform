import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { Car, Plus, Trash2, Edit, X } from "lucide-react";
import { Card, Btn, Field, Input, Spinner, EmptyState, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const EMPTY = { plate_number: "", vehicle_type: "", make: "", model: "", year: "", color: "", capacity: "", notes: "", status: "ACTIVE", assigned_driver_id: "" };

function VehicleForm({ initial, drivers, onClose, onSaved }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ ...EMPTY, ...(initial || {}) });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const save = async () => {
    if (busy) return;
    if (!form.plate_number.trim()) return toast.error(t("common.required"));
    setBusy(true);
    try {
      const payload = { ...form, assigned_driver_id: form.assigned_driver_id || null };
      if (initial?.id) {
        await api.put(`/provider/vehicles/${initial.id}`, payload);
      } else {
        await api.post("/provider/vehicles", payload);
      }
      toast.success(t("common.success"));
      onSaved && onSaved();
      onClose();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="vehicle-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl w-full max-w-lg p-6 shadow-xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-[#16233A]">{initial ? t("provider.editVehicle") : t("provider.addVehicle")}</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-500" /></button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label={t("provider.plateNumber")} required><Input data-testid="veh-plate" value={form.plate_number} onChange={set("plate_number")} className="force-ltr" /></Field>
          <Field label={t("provider.vehicleType")}><Input data-testid="veh-type" value={form.vehicle_type} onChange={set("vehicle_type")} /></Field>
          <Field label={t("provider.make")}><Input value={form.make} onChange={set("make")} /></Field>
          <Field label={t("provider.model")}><Input value={form.model} onChange={set("model")} /></Field>
          <Field label={t("provider.year")}><Input value={form.year} onChange={set("year")} className="force-ltr" /></Field>
          <Field label={t("provider.color")}><Input value={form.color} onChange={set("color")} /></Field>
          <Field label={t("provider.capacity")}><Input value={form.capacity} onChange={set("capacity")} /></Field>
          <Field label={t("common.status")}>
            <select value={form.status} onChange={set("status")} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#F1701E]">
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
              <option value="MAINTENANCE">MAINTENANCE</option>
            </select>
          </Field>
          <Field label={t("provider.assignedDriver")}>
            <select data-testid="veh-assigned" value={form.assigned_driver_id || ""} onChange={set("assigned_driver_id")} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#F1701E]">
              <option value="">{t("provider.unassigned")}</option>
              {drivers.map((d) => <option key={d.id} value={d.id}>{d.name || d.phone}</option>)}
            </select>
          </Field>
        </div>
        <div className="flex gap-2 mt-4">
          <Btn variant="secondary" onClick={onClose} disabled={busy} className="flex-1 justify-center">{t("common.cancel")}</Btn>
          <Btn variant="accent" onClick={save} disabled={busy} data-testid="save-vehicle-btn" className="flex-1 justify-center">{t("common.save")}</Btn>
        </div>
      </div>
    </div>
  );
}

export default function ProviderVehicles() {
  const { t } = useI18n();
  const [vehicles, setVehicles] = useState(null);
  const [drivers, setDrivers] = useState([]);
  const [modal, setModal] = useState(null);
  const [editing, setEditing] = useState(null);
  const load = async () => {
    try {
      const [{ data: vs }, { data: ds }] = await Promise.all([api.get("/provider/vehicles"), api.get("/provider/drivers")]);
      setVehicles(vs);
      setDrivers(ds);
    } catch { setVehicles([]); }
  };
  useEffect(() => { load(); }, []);
  const del = async (v) => {
    if (!window.confirm(t("provider.confirmDelete"))) return;
    try { await api.delete(`/provider/vehicles/${v.id}`); toast.success(t("common.success")); load(); }
    catch (e) { toast.error(apiErr(e)); }
  };
  if (vehicles === null) return <Spinner label={t("common.loading")} />;
  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={t("provider.vehicles")} action={<Btn variant="accent" data-testid="add-vehicle-btn" onClick={() => { setEditing(null); setModal(true); }}><Plus className="w-4 h-4" /> {t("provider.addVehicle")}</Btn>} />
      {vehicles.length === 0 ? <Card><EmptyState icon={Car} title={t("common.none")} /></Card> : (
        <div className="grid gap-3">
          {vehicles.map((v) => (
            <Card key={v.id} data-testid={`vehicle-${v.id}`} className="min-w-0 overflow-hidden">
              <div className="flex items-center justify-between gap-3 mb-2 min-w-0">
                <Link to={`/provider/vehicles/${v.id}`} className="font-bold text-[#16233A] truncate hover:text-[#F1701E] force-ltr">{v.plate_number}</Link>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${v.status === "ACTIVE" ? "bg-emerald-50 text-emerald-700" : v.status === "MAINTENANCE" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600"}`}>{v.status}</span>
              </div>
              <div className="text-sm text-slate-600 grid grid-cols-2 gap-2">
                <div>{t("provider.vehicleType")}: <b className="text-slate-700">{v.vehicle_type || "\u2014"}</b></div>
                <div>{t("provider.make")}: <b className="text-slate-700">{v.make || "\u2014"}</b></div>
                <div>{t("provider.model")}: <b className="text-slate-700">{v.model || "\u2014"}</b></div>
                <div>{t("provider.year")}: <b className="text-slate-700">{v.year || "\u2014"}</b></div>
                <div className="col-span-2">{t("provider.assignedDriver")}: <b className="text-slate-700">{v.assigned_driver?.name || t("provider.unassigned")}</b></div>
              </div>
              <div className="flex gap-2 mt-3">
                <Btn variant="secondary" onClick={() => { setEditing(v); setModal(true); }} data-testid={`edit-vehicle-${v.id}`}><Edit className="w-4 h-4" /> {t("common.edit")}</Btn>
                <Btn variant="ghost" onClick={() => del(v)} data-testid={`delete-vehicle-${v.id}`} className="text-red-600 hover:bg-red-50"><Trash2 className="w-4 h-4" /> {t("common.delete")}</Btn>
              </div>
            </Card>
          ))}
        </div>
      )}
      {modal && <VehicleForm initial={editing} drivers={drivers} onClose={() => setModal(false)} onSaved={load} />}
    </div>
  );
}
