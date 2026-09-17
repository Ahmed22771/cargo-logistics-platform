import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { DollarSign, TrendingUp, Users, Truck, Wallet, Settings } from "lucide-react";
import { Table } from "./AdminLayout";
import { Card, Btn, Spinner, PageHeader, Input, Field } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

export default function AdminFinance() {
  const { t, lang } = useI18n();
  const [stats, setStats] = useState(null);
  const [txns, setTxns] = useState([]);
  const [balances, setBalances] = useState([]);
  const [settings, setSettings] = useState(null);
  const [balRole, setBalRole] = useState("driver");
  const [typeFilter, setTypeFilter] = useState("");

  const loadTxns = (type) => api.get(`/admin/finance/transactions${type ? `?type=${type}` : ""}`).then(({ data }) => setTxns(data)).catch(() => setTxns([]));
  const loadBalances = (role) => api.get(`/admin/finance/balances?role=${role}`).then(({ data }) => setBalances(data)).catch(() => setBalances([]));

  useEffect(() => {
    api.get("/admin/finance/stats").then(({ data }) => setStats(data)).catch(() => setStats({}));
    api.get("/admin/finance/settings").then(({ data }) => setSettings(data)).catch(() => setSettings(null));
    loadTxns(""); loadBalances("driver");
  }, []);
  useEffect(() => { loadTxns(typeFilter); }, [typeFilter]);
  useEffect(() => { loadBalances(balRole); }, [balRole]);

  if (stats === null) return <Spinner label={t("common.loading")} />;
  const cur = stats.currency || "OMR";
  const cards = [
    { label: t("p11.fin.totalRevenue"), value: stats.total_revenue, icon: DollarSign, c: "text-emerald-600 bg-emerald-50" },
    { label: t("p11.fin.totalCommission"), value: stats.total_commission, icon: TrendingUp, c: "text-[#F1701E] bg-[#F1701E]/10" },
    { label: t("p11.fin.driverEarnings"), value: stats.driver_earnings, icon: Truck, c: "text-[#16233A] bg-[#16233A]/5" },
    { label: t("p11.fin.adjustments"), value: stats.adjustments, icon: Wallet, c: "text-blue-600 bg-blue-50" },
  ];

  const saveSettings = async () => {
    try { const { data } = await api.put("/admin/finance/settings", settings); setSettings(data); toast.success(t("common.success")); api.get("/admin/finance/stats").then(({ data }) => setStats(data)); }
    catch (e) { toast.error(apiErr(e)); }
  };

  const TYPES = ["", "customer_payment", "platform_commission", "driver_earning", "adjustment", "refund", "payout"];

  return (
    <div>
      <PageHeader title={t("p11.fin.title")} subtitle={t("p11.fin.ledgerNote")} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {cards.map((c, i) => (
          <Card key={i} data-testid={`fin-stat-${i}`} className="!p-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${c.c}`}><c.icon className="w-5 h-5" /></div>
            <div className="text-xl md:text-2xl font-extrabold text-[#16233A]">{(c.value ?? 0).toFixed(3)} <span className="text-sm font-semibold text-slate-400">{cur}</span></div>
            <div className="text-xs text-slate-500 mt-1">{c.label}</div>
          </Card>
        ))}
      </div>

      {settings && (
        <Card className="mb-6">
          <h2 className="font-bold text-[#16233A] mb-4 flex items-center gap-2"><Settings className="w-5 h-5 text-[#F1701E]" /> {t("p11.fin.commissionSettings")}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
            <Field label={t("p11.fin.commissionType")}>
              <select data-testid="commission-type" value={settings.commission_type} onChange={(e) => setSettings({ ...settings, commission_type: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white">
                <option value="percentage">{t("p11.fin.percentage")}</option><option value="fixed">{t("p11.fin.fixed")}</option>
              </select>
            </Field>
            <Field label={t("p11.fin.commissionValue")}><Input type="number" data-testid="commission-value" value={settings.commission_value} onChange={(e) => setSettings({ ...settings, commission_value: parseFloat(e.target.value) })} className="force-ltr" /></Field>
            <Field label={t("p11.fin.currency")}><Input data-testid="commission-currency" value={settings.currency} onChange={(e) => setSettings({ ...settings, currency: e.target.value })} className="force-ltr" /></Field>
          </div>
          <Btn variant="accent" onClick={saveSettings} data-testid="save-commission-btn" className="mt-4">{t("common.save")}</Btn>
        </Card>
      )}

      <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
        <h2 className="text-lg font-bold text-[#16233A]">{t("p11.fin.transactions")}</h2>
        <select data-testid="txn-type-filter" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
          {TYPES.map((ty) => <option key={ty} value={ty}>{ty ? t(`p11.fin.txn_${ty}`) : t("common.all")}</option>)}
        </select>
      </div>
      <Table testId="txns-table" rows={txns} empty={t("p11.fin.noTransactions")}
        columns={[t("p11.fin.type"), t("p11.fin.account"), t("p11.fin.gross"), t("p11.fin.commission"), t("p11.fin.net"), t("common.status")]}
        renderRow={(x) => (
          <tr key={x.id} data-testid={`txn-${x.id}`} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A]">{t(`p11.fin.txn_${x.type}`)}</td>
            <td className="px-4 py-3 text-slate-600">{x.account_name}</td>
            <td className="px-4 py-3 font-mono text-xs">{(x.gross ?? 0).toFixed(3)}</td>
            <td className="px-4 py-3 font-mono text-xs text-[#F1701E]">{(x.commission ?? 0).toFixed(3)}</td>
            <td className="px-4 py-3 font-mono text-xs font-bold">{(x.net ?? 0).toFixed(3)}</td>
            <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700">{x.status}</span></td>
          </tr>
        )}
      />

      <div className="flex items-center justify-between gap-3 mt-8 mb-3">
        <h2 className="text-lg font-bold text-[#16233A]">{t("p11.fin.balances")}</h2>
        <div className="flex gap-1">
          {["driver", "provider", "customer"].map((r) => (
            <button key={r} data-testid={`bal-role-${r}`} onClick={() => setBalRole(r)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${balRole === r ? "bg-[#16233A] text-white" : "bg-white border border-slate-200 text-slate-500"}`}>{t(`auth.${r}`)}</button>
          ))}
        </div>
      </div>
      <Table testId="balances-table" rows={balances} empty={t("p11.fin.noTransactions")}
        columns={[t("p11.rbac.name"), t("p11.fin.earned"), t("p11.fin.payouts"), t("p11.fin.available")]}
        renderRow={(b) => (
          <tr key={b.account_id} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A]">{b.company_name || b.name}</td>
            <td className="px-4 py-3 font-mono text-xs">{b.earned.toFixed(3)}</td>
            <td className="px-4 py-3 font-mono text-xs">{b.payouts.toFixed(3)}</td>
            <td className="px-4 py-3 font-mono text-xs font-bold text-emerald-600">{b.available.toFixed(3)} {cur}</td>
          </tr>
        )}
      />
    </div>
  );
}
