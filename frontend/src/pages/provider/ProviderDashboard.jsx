import React, { useEffect, useState } from "react";
import { Building2, Package, Truck, MapPin, Wallet } from "lucide-react";
import { Card, Spinner, PageHeader, EmptyState } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";

export default function ProviderDashboard() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [opps, setOpps] = useState([]);
  const [bids, setBids] = useState([]);
  const [transactions, setTransactions] = useState([]);
  useEffect(() => {
    api.get("/provider/summary").then(({ data }) => setSummary(data)).catch(() => setSummary({}));
    api.get("/provider/opportunities").then(({ data }) => setOpps(data)).catch(() => setOpps([]));
    api.get("/provider/bids").then(({ data }) => setBids(data)).catch(() => setBids([]));
    api.get("/provider/transactions").then(({ data }) => setTransactions(data)).catch(() => setTransactions([]));
  }, []);
  if (summary === null) return <Spinner label={t("common.loading")} />;
  const stats = [
    { label: t("provider.shipments"), value: opps.length, icon: Package, color: "text-[#F1701E] bg-[#F1701E]/10" },
    { label: t("nav.trips"), value: summary.trips || 0, icon: Truck, color: "text-[#16233A] bg-[#16233A]/5" },
    { label: t("provider.transactions"), value: transactions.length, icon: Wallet, color: "text-emerald-600 bg-emerald-50" },
  ];
  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={user?.company_name || t("nav.dashboard")} subtitle={<span className="flex items-center gap-1 min-w-0"><Building2 className="w-4 h-4 shrink-0" /> <span className="truncate">{user?.name}</span></span>} />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 md:gap-4 mb-6">
        {stats.map((s, i) => (
          <Card key={i} className="!p-4 min-w-0 overflow-hidden">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${s.color}`}><s.icon className="w-5 h-5" /></div>
            <div className="text-2xl md:text-3xl font-extrabold text-[#16233A]">{s.value}</div>
            <div className="text-xs md:text-sm text-slate-500 mt-1 truncate">{s.label}</div>
          </Card>
        ))}
      </div>
      {user?.service_areas?.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {user.service_areas.map((a, i) => <span key={i} className="inline-flex max-w-full items-center gap-1 bg-slate-100 rounded-full px-3 py-1 text-sm text-slate-600 truncate"><MapPin className="w-3.5 h-3.5 shrink-0 text-[#F1701E]" /> {a}</span>)}
        </div>
      )}
      <section className="mb-6 min-w-0">
        <h2 className="text-lg font-bold text-[#16233A] mb-3">{t("provider.shipments")}</h2>
        {opps.length === 0 ? <Card><EmptyState icon={Package} title={t("shipment.noShipments")} /></Card> : (
          <div className="grid gap-3 min-w-0">
            {opps.map((s) => (
              <Card key={s.id} data-testid={`opp-${s.id}`} className="min-w-0 overflow-hidden">
                <div className="flex items-center justify-between gap-3 mb-2 min-w-0"><h3 className="min-w-0 truncate font-bold text-[#16233A]">{s.title}</h3><StatusBadge status={s.status} /></div>
                <RouteInline pickup={s.pickup_location} delivery={s.delivery_location} />
              </Card>
            ))}
          </div>
        )}
      </section>
      <section className="mb-6 min-w-0">
        <h2 className="text-lg font-bold text-[#16233A] mb-3">{t("provider.bids")}</h2>
        {bids.length === 0 ? <Card><EmptyState icon={Package} title={t("provider.noBids")} /></Card> : (
          <div className="grid gap-3 min-w-0">
            {bids.map((bid) => (
              <Card key={bid.id} className="min-w-0 overflow-hidden">
                <div className="flex items-center justify-between gap-3 min-w-0"><h3 className="min-w-0 truncate font-bold text-[#16233A]">{bid.shipment?.title || bid.shipment_id}</h3><StatusBadge status={bid.status} /></div>
                <div className="text-sm text-slate-500 mt-2">{t("provider.amount")}: {bid.price} {t("common.currency")}</div>
              </Card>
            ))}
          </div>
        )}
      </section>
      <section className="min-w-0">
        <h2 className="text-lg font-bold text-[#16233A] mb-3">{t("provider.transactions")}</h2>
        {transactions.length === 0 ? <Card><EmptyState icon={Wallet} title={t("provider.noTransactions")} /></Card> : (
          <div className="grid gap-3 min-w-0">
            {transactions.map((txn) => (
              <Card key={txn.id} className="min-w-0 overflow-hidden !p-4">
                <div className="flex items-center justify-between gap-3 min-w-0"><span className="font-semibold text-[#16233A] truncate">{txn.description || txn.type}</span><span className="font-bold text-emerald-700 shrink-0">{txn.amount} {txn.currency || t("common.currency")}</span></div>
                <div className="text-xs text-slate-400 mt-1">{txn.created_at ? new Date(txn.created_at).toLocaleDateString() : "—"}</div>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
