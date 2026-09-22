import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, Search, Eye, ChevronLeft, ChevronRight } from "lucide-react";
import { Table } from "./AdminLayout";
import { Spinner, PageHeader, Input, Btn, Card } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

// Shared helpers for the Disputes screens (list + detail). Pure presentational /
// formatting only — ALL financial state comes from the backend APIs.
export function DisputeStatePill({ state }) {
  const { t } = useI18n();
  const cls = state === "OPEN"
    ? "bg-red-50 text-red-700 border-red-200"
    : "bg-emerald-50 text-emerald-700 border-emerald-200";
  return (
    <span data-testid={`dispute-state-${state}`} className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${cls}`}>
      {t(state === "OPEN" ? "disp.open" : "disp.resolved")}
    </span>
  );
}

export function fmtDate(x, lang) {
  if (!x) return "—";
  try {
    return new Date(x).toLocaleString(lang === "ar" ? "ar-OM" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return "—";
  }
}

export default function AdminDisputes() {
  const { t, lang, isRTL } = useI18n();
  const navigate = useNavigate();
  const [rows, setRows] = useState(null);
  const [providers, setProviders] = useState({});
  const [q, setQ] = useState("");
  const [stateFilter, setStateFilter] = useState("");

  const load = useCallback(() => {
    setRows(null);
    const qs = stateFilter ? `?status=${encodeURIComponent(stateFilter)}` : "";
    api.get(`/admin/disputes${qs}`).then(({ data }) => setRows(data || [])).catch(() => setRows([]));
  }, [stateFilter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    api.get("/admin/users?role=provider").then(({ data }) => {
      const m = {};
      (data || []).forEach((u) => { m[u.id] = u.company_name || u.name || u.id; });
      setProviders(m);
    }).catch(() => setProviders({}));
  }, []);

  const filtered = useMemo(() => {
    const list = rows || [];
    const s = q.trim().toLowerCase();
    if (!s) return list;
    return list.filter((d) =>
      [d.shipment_title, d.customer_name, d.driver_name, d.reason, d.trip_id]
        .some((v) => (v || "").toLowerCase().includes(s)));
  }, [rows, q]);

  if (rows === null) return <Spinner label={t("common.loading")} />;
  const Chevron = isRTL ? ChevronLeft : ChevronRight;
  const openDetail = (d) => navigate(`/admin/disputes/${d.trip_id}`);

  return (
    <div data-testid="admin-disputes-page">
      <PageHeader title={t("disp.title")} subtitle={t("disp.subtitle")}
        action={<Btn variant="secondary" data-testid="disputes-refresh" onClick={load}><RefreshCw className="w-4 h-4" /> {t("disp.refresh")}</Btn>} />

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative flex-1 min-w-[220px] max-w-sm">
          <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
          <Input data-testid="disputes-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("disp.searchPh")} className="ps-9" />
        </div>
        <select data-testid="disputes-state-filter" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white">
          <option value="">{t("disp.allStates")}</option>
          <option value="OPEN">{t("disp.open")}</option>
          <option value="RESOLVED">{t("disp.resolved")}</option>
        </select>
      </div>

      {/* Desktop table */}
      <div className="hidden md:block">
        <Table testId="disputes-table" rows={filtered} empty={t("disp.empty")}
          columns={[t("shipment.title"), t("disp.customer"), t("disp.driver"), t("disp.provider"), t("disp.amount"),
            t("disp.paymentStatus"), t("disp.disputeStatus"), t("disp.openedAt"), t("disp.resolvedAt"), ""]}
          renderRow={(d) => (
            <tr key={d.trip_id} data-testid={`dispute-row-${d.trip_id}`} onClick={() => openDetail(d)} className="hover:bg-slate-50 cursor-pointer">
              <td className="px-4 py-3 max-w-[200px]">
                <div className="font-semibold text-[#16233A] truncate">{d.shipment_title}</div>
                <div className="text-[10px] text-slate-400 font-mono" dir="ltr">#{(d.trip_id || "").slice(0, 8)}</div>
              </td>
              <td className="px-4 py-3 text-slate-600">{d.customer_name}</td>
              <td className="px-4 py-3 text-slate-600">{d.driver_name}</td>
              <td className="px-4 py-3 text-slate-600">{d.provider_id ? (providers[d.provider_id] || "—") : "—"}</td>
              <td className="px-4 py-3 font-mono text-xs font-bold">{Number(d.amount || 0).toFixed(3)} {t("common.currency")}</td>
              <td className="px-4 py-3">{d.payment_status ? <StatusBadge status={d.payment_status} /> : "—"}</td>
              <td className="px-4 py-3"><DisputeStatePill state={d.state} /></td>
              <td className="px-4 py-3 text-xs text-slate-400">{fmtDate(d.opened_at, lang)}</td>
              <td className="px-4 py-3 text-xs text-slate-400">{fmtDate(d.resolved_at, lang)}</td>
              <td className="px-4 py-3"><Eye className="w-4 h-4 text-slate-400" /></td>
            </tr>
          )}
        />
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3" data-testid="disputes-cards">
        {filtered.length === 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-slate-400" data-testid="disputes-cards-empty">{t("disp.empty")}</div>
        )}
        {filtered.map((d) => (
          <Card key={d.trip_id} data-testid={`dispute-card-${d.trip_id}`} className="!p-4 cursor-pointer" onClick={() => openDetail(d)}>
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="min-w-0">
                <div className="font-bold text-[#16233A] truncate">{d.shipment_title}</div>
                <div className="text-[10px] text-slate-400 font-mono" dir="ltr">#{(d.trip_id || "").slice(0, 8)}</div>
              </div>
              <DisputeStatePill state={d.state} />
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><span className="text-slate-400">{t("disp.customer")}: </span><span className="font-semibold text-slate-700">{d.customer_name}</span></div>
              <div><span className="text-slate-400">{t("disp.driver")}: </span><span className="font-semibold text-slate-700">{d.driver_name}</span></div>
              <div><span className="text-slate-400">{t("disp.amount")}: </span><span className="font-mono font-bold">{Number(d.amount || 0).toFixed(3)} {t("common.currency")}</span></div>
              <div className="flex items-center gap-1"><span className="text-slate-400">{t("disp.paymentStatus")}: </span>{d.payment_status ? <StatusBadge status={d.payment_status} /> : "—"}</div>
            </div>
            <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100">
              <span className="text-[11px] text-slate-400">{fmtDate(d.opened_at, lang)}</span>
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#F1701E]">{t("disp.viewDetails")} <Chevron className="w-3.5 h-3.5" /></span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
