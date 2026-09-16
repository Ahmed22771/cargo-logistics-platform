import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Search, Star, Eye, X } from "lucide-react";
import { Table } from "./AdminLayout";
import { Btn, Spinner, PageHeader, Input, Textarea, Field } from "../../components/ui-kit";
import { VerificationBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

export default function AdminDrivers() {
  const { t } = useI18n();
  const [drivers, setDrivers] = useState(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [detail, setDetail] = useState(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/admin/drivers").then(({ data }) => setDrivers(data)).catch(() => setDrivers([]));
  useEffect(() => { load(); }, []);
  if (drivers === null) return <Spinner label={t("common.loading")} />;

  const filtered = drivers.filter((d) =>
    (filter === "all" || d.verification_status === filter) &&
    (d.name?.toLowerCase().includes(q.toLowerCase()) || (d.phone || "").includes(q))
  );

  const act = async (driver, action) => {
    setBusy(true);
    try {
      await api.post(`/admin/drivers/${driver.id}/verify`, { action, notes });
      toast.success(t("common.success")); setNotes(""); setDetail(null); await load();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  const FILTERS = ["all", "UNDER_REVIEW", "PENDING", "APPROVED", "REJECTED", "SUSPENDED"];

  return (
    <div>
      <PageHeader title={t("admin.manageDrivers")} />
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
          <Input data-testid="driver-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("common.search")} className="ps-9" />
        </div>
        <div className="flex gap-1 flex-wrap">
          {FILTERS.map((f) => (
            <button key={f} data-testid={`filter-${f}`} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${filter === f ? "bg-[#16233A] text-white" : "bg-white border border-slate-200 text-slate-500"}`}>
              {f === "all" ? t("common.all") : t(`verification.${f}`)}
            </button>
          ))}
        </div>
      </div>

      <Table testId="drivers-table" rows={filtered}
        columns={[t("auth.name"), t("auth.phone"), t("verification.status"), t("bid.rating"), t("bid.completedTrips"), ""]}
        renderRow={(d) => (
          <tr key={d.id} data-testid={`driver-row-${d.id}`} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A]">{d.name}</td>
            <td className="px-4 py-3 font-mono text-xs force-ltr">{d.phone}</td>
            <td className="px-4 py-3"><VerificationBadge status={d.verification_status} /></td>
            <td className="px-4 py-3"><span className="flex items-center gap-1"><Star className="w-3.5 h-3.5 fill-[#F1701E] text-[#F1701E]" /> {d.rating || 0}</span></td>
            <td className="px-4 py-3">{d.completed_trips || 0}</td>
            <td className="px-4 py-3"><Btn variant="secondary" data-testid={`view-driver-${d.id}`} onClick={() => { setDetail(d); setNotes(d.admin_notes || ""); }} className="!py-1.5 !px-3"><Eye className="w-4 h-4" /></Btn></td>
          </tr>
        )}
      />

      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="driver-detail-modal">
          <div className="absolute inset-0 bg-black/40" onClick={() => setDetail(null)} />
          <div className="relative bg-white rounded-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-auto">
            <div className="flex items-start justify-between mb-4">
              <div><h2 className="font-bold text-lg text-[#16233A]">{detail.name}</h2><p className="text-sm text-slate-400 font-mono force-ltr">{detail.phone}</p></div>
              <button onClick={() => setDetail(null)}><X className="w-5 h-5 text-slate-400" /></button>
            </div>
            <div className="mb-4"><VerificationBadge status={detail.verification_status} /></div>
            {detail.vehicle?.type && (
              <div className="bg-slate-50 rounded-lg p-3 mb-4 text-sm">
                <div className="font-semibold text-slate-600 mb-1">{t("nav.vehicle")}</div>
                <div className="text-slate-500">{detail.vehicle.type} · {detail.vehicle.plate} · {detail.vehicle.model}</div>
              </div>
            )}
            <div className="mb-4">
              <div className="font-semibold text-slate-600 text-sm mb-2">{t("nav.documents")}</div>
              {(detail.documents || []).length === 0 ? <p className="text-sm text-slate-400">{t("common.none")}</p> :
                (detail.documents || []).map((doc, i) => (
                  <div key={i} className="flex items-center justify-between text-sm py-1.5 border-b last:border-0">
                    <span className="text-slate-600">{t(`verification.${doc.type === "driving_license" ? "drivingLicense" : doc.type === "vehicle_registration" ? "vehicleReg" : "insurance"}`)}</span>
                    <span className="font-mono text-xs text-slate-400 force-ltr">{doc.reference} · {doc.expiry}</span>
                  </div>
                ))}
            </div>
            <Field label={t("admin.adminNotes")}><Textarea rows={2} data-testid="admin-notes" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
            <div className="grid grid-cols-2 gap-2 mt-4">
              <Btn variant="accent" onClick={() => act(detail, "approve")} disabled={busy} data-testid="approve-driver-btn">{t("admin.approve")}</Btn>
              <Btn variant="danger" onClick={() => act(detail, "reject")} disabled={busy} data-testid="reject-driver-btn">{t("admin.reject")}</Btn>
              <Btn variant="secondary" onClick={() => act(detail, "request_changes")} disabled={busy} data-testid="request-changes-btn">{t("admin.requestChanges")}</Btn>
              <Btn variant="outline" onClick={() => act(detail, "suspend")} disabled={busy} data-testid="suspend-driver-btn" className="text-red-600 border-red-300">{t("admin.suspend")}</Btn>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
