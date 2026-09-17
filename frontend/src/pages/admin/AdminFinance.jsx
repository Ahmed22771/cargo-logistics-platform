import React, { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { DollarSign, TrendingUp, Truck, Building2, RotateCcw, Wallet, Settings, X, Plus, Undo2, Eye } from "lucide-react";
import { Table } from "./AdminLayout";
import { Card, Btn, Spinner, PageHeader, Input, Field, Textarea } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const TYPES = ["", "customer_payment", "platform_commission", "driver_earning", "provider_earning", "adjustment", "refund", "reversal", "payout"];
const REVERSIBLE = ["adjustment", "customer_payment", "driver_earning", "provider_earning", "platform_commission", "refund"];

function Modal({ title, onClose, children, wide }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className={`relative bg-white rounded-2xl w-full ${wide ? "max-w-2xl" : "max-w-md"} p-6 max-h-[90vh] overflow-y-auto`} data-testid="fin-modal">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg text-[#16233A]">{title}</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function AdminFinance() {
  const { t, lang } = useI18n();
  const [perms, setPerms] = useState([]);
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState(false);
  const [txns, setTxns] = useState(null);
  const [balances, setBalances] = useState([]);
  const [settings, setSettings] = useState(null);
  const [balRole, setBalRole] = useState("driver");
  const [f, setF] = useState({ type: "", status: "", q: "", date_from: "", date_to: "" });
  const [adjust, setAdjust] = useState(null);
  const [account, setAccount] = useState(null);
  const [busy, setBusy] = useState(false);

  const can = (p) => perms.includes(p);

  const loadStats = useCallback(() => { setStatsError(false); api.get("/admin/finance/stats").then(({ data }) => setStats(data)).catch(() => { setStats({}); setStatsError(true); }); }, []);
  const loadTxns = useCallback(() => {
    const p = new URLSearchParams();
    Object.entries(f).forEach(([k, v]) => { if (v) p.set(k, v); });
    setTxns(null);
    api.get(`/admin/finance/transactions?${p.toString()}`).then(({ data }) => setTxns(data)).catch(() => setTxns([]));
  }, [f]);
  const loadBalances = useCallback((role) => api.get(`/admin/finance/balances?role=${role}`).then(({ data }) => setBalances(data)).catch(() => setBalances([])), []);

  useEffect(() => { api.get("/admin/me/permissions").then(({ data }) => setPerms(data.permissions || [])).catch(() => setPerms([])); }, []);
  useEffect(() => { loadStats(); api.get("/admin/finance/settings").then(({ data }) => setSettings(data)).catch(() => setSettings(null)); }, [loadStats]);
  useEffect(() => { loadTxns(); }, [loadTxns]);
  useEffect(() => { loadBalances(balRole); }, [balRole, loadBalances]);

  if (stats === null) return <Spinner label={t("common.loading")} />;
  const cur = stats.currency || "OMR";

  const cards = [
    { label: t("p11.fin.totalRevenue"), value: stats.total_revenue, icon: DollarSign, c: "text-emerald-600 bg-emerald-50" },
    { label: t("p11.fin.totalCommission"), value: stats.total_commission, icon: TrendingUp, c: "text-[#F1701E] bg-[#F1701E]/10" },
    { label: t("p11.fin.driverEarnings"), value: stats.driver_earnings, icon: Truck, c: "text-[#16233A] bg-[#16233A]/5" },
    { label: t("p11.fin.providerEarnings"), value: stats.provider_earnings, icon: Building2, c: "text-purple-600 bg-purple-50" },
    { label: t("p11.fin.refunds"), value: stats.refunds, icon: RotateCcw, c: "text-red-500 bg-red-50" },
    { label: t("p11.fin.adjustments"), value: stats.adjustments, icon: Wallet, c: "text-blue-600 bg-blue-50" },
  ];

  const saveSettings = async () => {
    try { const { data } = await api.put("/admin/finance/settings", settings); setSettings(data); toast.success(t("common.success")); loadStats(); }
    catch (e) { toast.error(apiErr(e)); }
  };

  const submitAdjust = async () => {
    if (!adjust.account_id || !adjust.amount || !adjust.reason) { toast.error(t("common.required")); return; }
    setBusy(true);
    try {
      const url = adjust.mode === "refund" ? "/admin/finance/refund" : "/admin/finance/adjust";
      await api.post(url, { account_id: adjust.account_id, account_role: adjust.account_role, amount: parseFloat(adjust.amount), reason: adjust.reason, description: adjust.description });
      toast.success(t("common.success")); setAdjust(null); loadTxns(); loadStats(); loadBalances(balRole);
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  const reverse = async (x) => {
    if (!window.confirm(t("p11.fin.confirmReverse"))) return;
    const reason = window.prompt(t("p11.fin.reason"));
    if (!reason) return;
    try { await api.post(`/admin/finance/transactions/${x.id}/reverse`, { reason }); toast.success(t("common.success")); loadTxns(); loadStats(); loadBalances(balRole); }
    catch (e) { toast.error(apiErr(e)); }
  };

  const viewAccount = async (id) => {
    try { const { data } = await api.get(`/admin/finance/account/${id}`); setAccount(data); }
    catch (e) { toast.error(apiErr(e)); }
  };

  const openAdjust = (mode, role, account_id) => setAdjust({ mode, account_role: role || "driver", account_id: account_id || "", amount: "", reason: "", description: "" });

  return (
    <div>
      <PageHeader title={t("p11.fin.title")} subtitle={t("p11.fin.ledgerNote")}
        action={(can("finance.adjust") || can("finance.refund")) && (
          <div className="flex gap-2">
            {can("finance.adjust") && <Btn variant="secondary" data-testid="open-adjust-btn" onClick={() => openAdjust("adjust", "driver")}><Plus className="w-4 h-4" /> {t("p11.fin.createAdjustment")}</Btn>}
            {can("finance.refund") && <Btn variant="accent" data-testid="open-refund-btn" onClick={() => openAdjust("refund", "customer")}><RotateCcw className="w-4 h-4" /> {t("p11.fin.refundAction")}</Btn>}
          </div>
        )} />

      {statsError ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-red-500 mb-6" data-testid="fin-stats-error">
          {t("p11.fin.loadError")} <button onClick={loadStats} className="text-[#F1701E] font-semibold ms-2">{t("p11.fin.retry")}</button>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
          {cards.map((c, i) => (
            <Card key={i} data-testid={`fin-stat-${i}`} className="!p-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${c.c}`}><c.icon className="w-5 h-5" /></div>
              <div className="text-lg md:text-xl font-extrabold text-[#16233A]">{(c.value ?? 0).toFixed(3)} <span className="text-xs font-semibold text-slate-400">{cur}</span></div>
              <div className="text-xs text-slate-500 mt-1">{c.label}</div>
            </Card>
          ))}
        </div>
      )}

      {settings && can("finance.commission") && (
        <Card className="mb-6">
          <h2 className="font-bold text-[#16233A] mb-4 flex items-center gap-2"><Settings className="w-5 h-5 text-[#F1701E]" /> {t("p11.fin.commissionSettings")}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
            <Field label={t("p11.fin.commissionType")}>
              <select data-testid="commission-type" value={settings.commission_type} onChange={(e) => setSettings({ ...settings, commission_type: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white">
                <option value="percentage">{t("p11.fin.percentage")}</option>
                <option value="fixed">{t("p11.fin.fixed")}</option>
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
        <div className="flex flex-wrap gap-2">
          <input data-testid="txn-search" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} placeholder={t("p11.fin.searchTxn")} className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white" />
          <select data-testid="txn-type-filter" value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
            {TYPES.map((ty) => <option key={ty} value={ty}>{ty ? t(`p11.fin.txn_${ty}`) : t("p11.fin.allTypes")}</option>)}
          </select>
          <input type="date" data-testid="txn-date-from" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} className="border border-slate-300 rounded-lg px-2 py-2 text-sm bg-white force-ltr" />
          <input type="date" data-testid="txn-date-to" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} className="border border-slate-300 rounded-lg px-2 py-2 text-sm bg-white force-ltr" />
        </div>
      </div>
      {txns === null ? <Spinner label={t("common.loading")} /> : (
        <Table testId="txns-table" rows={txns} empty={t("p11.fin.noTransactions")}
          columns={[t("p11.fin.type"), t("p11.fin.account"), t("p11.fin.gross"), t("p11.fin.commission"), t("p11.fin.net"), t("common.status"), t("p11.fin.date"), ""]}
          renderRow={(x) => (
            <tr key={x.id} data-testid={`txn-${x.id}`} className={`hover:bg-slate-50 ${x.reversed ? "opacity-60" : ""}`}>
              <td className="px-4 py-3 font-semibold text-[#16233A]">{t(`p11.fin.txn_${x.type}`)}{x.reversed && <span className="ms-1 text-[10px] text-red-500">({t("p11.fin.reversed")})</span>}</td>
              <td className="px-4 py-3 text-slate-600">{x.account_name}</td>
              <td className="px-4 py-3 font-mono text-xs">{(x.gross ?? 0).toFixed(3)}</td>
              <td className="px-4 py-3 font-mono text-xs text-[#F1701E]">{(x.commission ?? 0).toFixed(3)}</td>
              <td className="px-4 py-3 font-mono text-xs font-bold">{(x.net ?? 0).toFixed(3)}</td>
              <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700">{x.status}</span></td>
              <td className="px-4 py-3 text-xs text-slate-400 font-mono">{x.created_at ? new Date(x.created_at).toLocaleDateString(lang === "ar" ? "ar-OM" : "en-GB") : "\u2014"}</td>
              <td className="px-4 py-3">{can("finance.reverse") && !x.reversed && x.type !== "reversal" && REVERSIBLE.includes(x.type) && <button data-testid={`txn-reverse-${x.id}`} onClick={() => reverse(x)} title={t("p11.fin.reverse")} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Undo2 className="w-4 h-4" /></button>}</td>
            </tr>
          )}
        />
      )}

      <div className="flex items-center justify-between gap-3 mt-8 mb-3">
        <h2 className="text-lg font-bold text-[#16233A]">{t("p11.fin.balances")}</h2>
        <div className="flex gap-1">
          {["driver", "provider", "customer"].map((r) => (
            <button key={r} data-testid={`bal-role-${r}`} onClick={() => setBalRole(r)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${balRole === r ? "bg-[#16233A] text-white" : "bg-white border border-slate-200 text-slate-500"}`}>{t(`auth.${r}`)}</button>
          ))}
        </div>
      </div>
      <Table testId="balances-table" rows={balances} empty={t("p11.fin.noTransactions")}
        columns={[t("p11.rbac.name"), t("p11.fin.earned"), t("p11.fin.payouts"), t("p11.fin.available"), ""]}
        renderRow={(b) => (
          <tr key={b.account_id} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A]">{b.company_name || b.name}</td>
            <td className="px-4 py-3 font-mono text-xs">{b.earned.toFixed(3)}</td>
            <td className="px-4 py-3 font-mono text-xs">{b.payouts.toFixed(3)}</td>
            <td className="px-4 py-3 font-mono text-xs font-bold text-emerald-600">{b.available.toFixed(3)} {cur}</td>
            <td className="px-4 py-3">
              <div className="flex items-center gap-1.5">
                <button data-testid={`view-account-${b.account_id}`} onClick={() => viewAccount(b.account_id)} title={t("p11.fin.viewAccount")} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500"><Eye className="w-4 h-4" /></button>
                {can("finance.adjust") && <button data-testid={`bal-adjust-${b.account_id}`} onClick={() => openAdjust("adjust", balRole, b.account_id)} title={t("p11.fin.createAdjustment")} className="p-1.5 rounded-lg hover:bg-slate-100 text-blue-600"><Plus className="w-4 h-4" /></button>}
              </div>
            </td>
          </tr>
        )}
      />

      {adjust && (
        <Modal onClose={() => setAdjust(null)} title={adjust.mode === "refund" ? t("p11.fin.refundAction") : t("p11.fin.createAdjustment")}>
          <div className="space-y-4">
            <Field label={t("p11.fin.account")}>
              <select data-testid="adjust-role" value={adjust.account_role} onChange={(e) => setAdjust({ ...adjust, account_role: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white">
                <option value="driver">{t("auth.driver")}</option>
                <option value="provider">{t("auth.provider")}</option>
                <option value="customer">{t("auth.customer")}</option>
              </select>
            </Field>
            <Field label={`${t("p11.fin.account")} ID`} required><Input data-testid="adjust-account-id" value={adjust.account_id} onChange={(e) => setAdjust({ ...adjust, account_id: e.target.value })} className="force-ltr" /></Field>
            <Field label={t("p11.fin.amount")} required hint={cur}><Input type="number" data-testid="adjust-amount" value={adjust.amount} onChange={(e) => setAdjust({ ...adjust, amount: e.target.value })} className="force-ltr" /></Field>
            <Field label={t("p11.fin.reason")} required><Input data-testid="adjust-reason" value={adjust.reason} onChange={(e) => setAdjust({ ...adjust, reason: e.target.value })} /></Field>
            <Field label={t("p11.fin.description")}><Textarea data-testid="adjust-description" rows={2} value={adjust.description} onChange={(e) => setAdjust({ ...adjust, description: e.target.value })} /></Field>
            <Btn variant="accent" onClick={submitAdjust} disabled={busy} data-testid="adjust-submit" className="w-full">{t("p11.fin.submit")}</Btn>
          </div>
        </Modal>
      )}

      {account && (
        <Modal onClose={() => setAccount(null)} title={t("p11.fin.accountDetail")} wide>
          <div className="space-y-4">
            <div className="font-bold text-[#16233A]">{account.user ? (account.user.company_name || account.user.name) : account.account_id}
              <span className="ms-2 text-xs font-normal text-slate-400">{account.user ? t(`auth.${account.user.role}`) : ""}</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[[t("p11.fin.balance"), account.totals.balance], [t("p11.fin.earned"), account.totals.earned], [t("p11.fin.totalPaid"), account.totals.paid], [t("p11.fin.commission"), account.totals.commission], [t("p11.fin.refunds"), account.totals.refunds], [t("p11.fin.adjustments"), account.totals.adjustments]].map(([l, v], i) => (
                <div key={i} className="border border-slate-100 rounded-lg p-2.5"><div className="text-xs text-slate-400">{l}</div><div className="font-bold text-slate-700 font-mono text-sm">{(v ?? 0).toFixed(3)} {account.currency}</div></div>
              ))}
            </div>
            <Table testId="account-txns-table" rows={account.transactions} empty={t("p11.fin.noTransactions")}
              columns={[t("p11.fin.type"), t("p11.fin.amount"), t("common.status"), t("p11.fin.date")]}
              renderRow={(x) => (
                <tr key={x.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-semibold text-[#16233A]">{t(`p11.fin.txn_${x.type}`)}{x.reversed && <span className="ms-1 text-[10px] text-red-500">({t("p11.fin.reversed")})</span>}</td>
                  <td className="px-4 py-2.5 font-mono text-xs font-bold">{(x.amount ?? 0).toFixed(3)} {account.currency}</td>
                  <td className="px-4 py-2.5"><span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700">{x.status}</span></td>
                  <td className="px-4 py-2.5 text-xs text-slate-400 font-mono">{x.created_at ? new Date(x.created_at).toLocaleDateString(lang === "ar" ? "ar-OM" : "en-GB") : "\u2014"}</td>
                </tr>
              )}
            />
          </div>
        </Modal>
      )}
    </div>
  );
}
