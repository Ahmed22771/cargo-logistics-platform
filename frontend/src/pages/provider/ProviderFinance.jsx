import React, { useEffect, useMemo, useState } from "react";
import { Wallet } from "lucide-react";
import { Card, Spinner, EmptyState, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

const TABS = [
  { key: "ALL", label: "common.all" },
  { key: "HELD", label: "provider.held" },
  { key: "COMPLETED", label: "provider.completed" },
];

export default function ProviderFinance() {
  const { t } = useI18n();
  const [txns, setTxns] = useState(null);
  const [summary, setSummary] = useState({});
  const [tab, setTab] = useState("ALL");
  useEffect(() => {
    (async () => {
      try {
        const [{ data: sm }, { data: tx }] = await Promise.all([
          api.get("/provider/finance/summary"),
          api.get("/provider/transactions"),
        ]);
        setSummary(sm);
        setTxns(tx);
      } catch { setTxns([]); }
    })();
  }, []);
  const cur = t("common.currency");
  const fmt = (n) => `${Number(n || 0).toFixed(3)} ${cur}`;
  const filtered = useMemo(() => (txns || []).filter((tr) => tab === "ALL" || (tr.status || "").toUpperCase() === tab), [txns, tab]);
  if (txns === null) return <Spinner label={t("common.loading")} />;
  const stats = [
    { label: t("provider.totalEarnings"), value: fmt(summary.total_earnings), color: "text-emerald-700 bg-emerald-50" },
    { label: t("provider.held"), value: fmt(summary.held), color: "text-indigo-700 bg-indigo-50" },
    { label: t("provider.completed"), value: fmt(summary.completed), color: "text-blue-700 bg-blue-50" },
    { label: t("provider.platformCommission"), value: fmt(summary.platform_commission), color: "text-amber-700 bg-amber-50" },
    { label: t("provider.netEarnings"), value: fmt(summary.net_earnings), color: "text-[#F1701E] bg-orange-50" },
  ];
  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={t("provider.finance")} />
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        {stats.map((s, i) => (
          <Card key={i} className="!p-4 min-w-0 overflow-hidden">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-2 ${s.color}`}><Wallet className="w-4 h-4" /></div>
            <div className="text-lg md:text-xl font-extrabold text-[#16233A] truncate">{s.value}</div>
            <div className="text-xs text-slate-500 mt-1 truncate">{s.label}</div>
          </Card>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        {TABS.map((tab_) => (
          <button key={tab_.key} data-testid={`finance-tab-${tab_.key}`} onClick={() => setTab(tab_.key)}
            className={`px-3 py-1.5 rounded-lg text-sm font-semibold border ${tab === tab_.key ? "bg-[#16233A] text-white border-[#16233A]" : "bg-white text-slate-600 border-slate-200"}`}>
            {t(tab_.label) || tab_.key}
          </button>
        ))}
      </div>
      {filtered.length === 0 ? <Card><EmptyState icon={Wallet} title={t("provider.noTransactions")} /></Card> : (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-start">
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="text-start py-2 px-2">{t("common.date")}</th>
                <th className="text-start py-2 px-2">{t("nav.trips")}</th>
                <th className="text-start py-2 px-2">{t("common.status")}</th>
                <th className="text-start py-2 px-2">{t("provider.amount")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((tr) => (
                <tr key={tr.id} className="border-b border-slate-100">
                  <td className="py-2 px-2 text-xs text-slate-500">{tr.created_at ? new Date(tr.created_at).toLocaleString() : "\u2014"}</td>
                  <td className="py-2 px-2">{tr.description || tr.type}</td>
                  <td className="py-2 px-2"><span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{tr.status || "\u2014"}</span></td>
                  <td className="py-2 px-2 font-bold text-emerald-700">{fmt(tr.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
