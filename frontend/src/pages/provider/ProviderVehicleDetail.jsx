import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Car, FileText, User } from "lucide-react";
import { Card, Spinner, PageHeader, Btn } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

export default function ProviderVehicleDetail() {
  const { id } = useParams();
  const { t } = useI18n();
  const [vehicle, setVehicle] = useState(null);
  const [docs, setDocs] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [busy, setBusy] = useState(false);
  const [selectedDriver, setSelectedDriver] = useState("");
  const load = async () => {
    try {
      const [{ data: v }, { data: ds }] = await Promise.all([api.get(`/provider/vehicles/${id}`), api.get("/provider/drivers")]);
      setVehicle(v);
      setSelectedDriver(v.assigned_driver_id || "");
      setDrivers(ds);
      // vehicle-scoped documents (owner = provider, vehicle_id filter)
      const { data: allDocs } = await api.get("/documents/mine");
      setDocs((allDocs || []).filter((d) => d.vehicle_id === id));
    } catch (e) { toast.error(apiErr(e)); }
  };
  useEffect(() => { load(); }, [id]);
  const assign = async () => {
    setBusy(true);
    try {
      await api.post(`/provider/vehicles/${id}/assign`, { driver_id: selectedDriver || null });
      toast.success(t("common.success"));
      load();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  if (!vehicle) return <Spinner label={t("common.loading")} />;
  return (
    <div className="min-w-0 overflow-x-hidden">
      <Link to="/provider/vehicles" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"><ArrowLeft className="w-4 h-4" /> {t("common.back")}</Link>
      <PageHeader title={<span className="force-ltr">{vehicle.plate_number}</span>} subtitle={<span className="flex items-center gap-1"><Car className="w-4 h-4" /> {vehicle.vehicle_type || t("provider.vehicle")}</span>} />
      <div className="grid gap-4">
        <Card>
          <h3 className="font-bold text-[#16233A] mb-3">{t("provider.vehicleDetails")}</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><div className="text-slate-400">{t("provider.make")}</div><div className="font-semibold">{vehicle.make || "\u2014"}</div></div>
            <div><div className="text-slate-400">{t("provider.model")}</div><div className="font-semibold">{vehicle.model || "\u2014"}</div></div>
            <div><div className="text-slate-400">{t("provider.year")}</div><div className="font-semibold force-ltr">{vehicle.year || "\u2014"}</div></div>
            <div><div className="text-slate-400">{t("provider.color")}</div><div className="font-semibold">{vehicle.color || "\u2014"}</div></div>
            <div><div className="text-slate-400">{t("provider.capacity")}</div><div className="font-semibold">{vehicle.capacity || "\u2014"}</div></div>
            <div><div className="text-slate-400">{t("common.status")}</div><div className="font-semibold">{vehicle.status}</div></div>
          </div>
        </Card>
        <Card>
          <h3 className="font-bold text-[#16233A] mb-3 flex items-center gap-2"><User className="w-4 h-4" /> {t("provider.assignedDriver")}</h3>
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            <select value={selectedDriver} onChange={(e) => setSelectedDriver(e.target.value)} data-testid="veh-detail-assign-select"
              className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#F1701E]">
              <option value="">{t("provider.unassigned")}</option>
              {drivers.map((d) => <option key={d.id} value={d.id}>{d.name || d.phone}</option>)}
            </select>
            <Btn variant="accent" onClick={assign} disabled={busy} data-testid="veh-detail-assign-btn">{t("common.save")}</Btn>
          </div>
        </Card>
        <Card>
          <h3 className="font-bold text-[#16233A] mb-3 flex items-center gap-2"><FileText className="w-4 h-4" /> {t("provider.viewDocs")}</h3>
          {docs.length === 0 ? <p className="text-sm text-slate-500">{t("common.none")}</p> : (
            <div className="grid gap-2">
              {docs.map((d) => (
                <div key={d.id} className="border border-slate-200 rounded-lg p-3 flex items-center justify-between gap-3">
                  <div className="min-w-0"><div className="font-semibold text-[#16233A] truncate">{d.doc_type_name_ar || d.doc_type_key}</div><div className="text-xs text-slate-400">{d.reference || "\u2014"} \u00b7 {d.expiry || "\u2014"}</div></div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${d.status === "APPROVED" ? "bg-emerald-50 text-emerald-700" : d.status === "REJECTED" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>{d.status}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
