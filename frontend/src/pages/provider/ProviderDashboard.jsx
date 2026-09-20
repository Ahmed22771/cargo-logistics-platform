import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Building2, Package, Gavel, Truck, Car, Users, Wallet, FileText } from "lucide-react";
import { Card, Spinner, PageHeader, EmptyState } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";

const QUICK = [
  { to: "/provider/available", key: "available", label: "provider.availableShipments", icon: Package, color: "text-blue-700 bg-blue-50" },
  { to: "/provider/offers", key: "offers", label: "provider.offers", icon: Gavel, color: "text-amber-700 bg-amber-50" },
  { to: "/provider/vehicles", key: "vehicles", label: "provider.vehicles", icon: Car, color: "text-indigo-700 bg-indigo-50" },
  { to: "/provider/drivers", key: "drivers", label: "provider.drivers", icon: Users, color: "text-orange-700 bg-orange-50" },
  { to: "/provider/finance", key: "finance", label: "provider.finance", icon: Wallet, color: "text-emerald-700 bg-emerald-50" },
];

export default function ProviderDashboard() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [state, setState] = useState({ loading: true, summary: null, opps: [], bids: [], txns: [], trips: [], notifs: [], finance: null });

  useEffect(() => {
    let stop = false;
    (async () => {
      const safe = async (p, fb) => { try { return (await p).data; } catch { return fb; } };
      const [summary, opps, bids, txns, trips, notifs, finance] = await Promise.all([
        safe(api.get("/provider/summary"), {}),
        safe(api.get("/provider/opportunities"), []),
        safe(api.get("/provider/bids"), []),
        safe(api.get("/provider/transactions"), []),
        safe(api.get("/provider/trips"), []),
        safe(api.get("/notifications"), []),
        safe(api.get("/provider/finance/summary"), {}),
      ]);
      if (!stop) setState({ loading: false, summary, opps, bids, txns, trips, notifs, finance });
    })();
    return () => { stop = true; };
  }, []);

  if (state.loading) return <Spinner label={t("common.loading")} />;
  const activeTripStates = new Set(["DRIVER_ASSIGNED", "PICKUP_ARRIVED", "PICKED_UP", "IN_TRANSIT", "DRIVER_ARRIVED_DESTINATION", "DELIVERED_PENDING_CONFIRMATION"]);
  const active = state.trips.filter((tr) => activeTripStates.has(tr.status)).length;
  const completed = state.trips.filter((tr) => tr.status === "COMPLETED").length;
  const fin = state.finance || {};
  const cur = t("common.currency");
  const fmt = (n) => `${Number(n || 0).toFixed(3)} ${cur}`;

  const stats = [
    { key: "opps", label: t("provider.availableShipments"), value: state.opps.length, icon: Package, color: "text-blue-700 bg-blue-50" },
    { key: "offers", label: t("provider.offers"), value: state.bids.length, icon: Gavel, color: "text-amber-700 bg-amber-50" },
    { key: "active", label: t("provider.activeTrips"), value: active, icon: Truck, color: "text-orange-700 bg-orange-50" },
    { key: "completed", label: t("provider.completedTrips"), value: completed, icon: Truck, color: "text-emerald-700 bg-emerald-50" },
    { key: "earnings", label: t("provider.totalEarnings"), value: fmt(fin.total_earnings), icon: Wallet, color: "text-emerald-700 bg-emerald-50" },
    { key: "held", label: t("provider.held"), value: fmt(fin.held), icon: Wallet, color: "text-indigo-700 bg-indigo-50" },
  ];

  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={user?.company_name || t("provider.dashboard")} subtitle={<span className="flex items-center gap-1 min-w-0"><Building2 className="w-4 h-4 shrink-0" /> <span className="truncate">{user?.name}</span></span>} />

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 md:gap-4 mb-6">
        {stats.map((s) => (
          <Card key={s.key} data-testid={`provider-stat-${s.key}`} className="!p-4 min-w-0 overflow-hidden">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${s.color}`}><s.icon className="w-5 h-5" /></div>
            <div className="text-xl md:text-2xl font-extrabold text-[#16233A] truncate">{s.value}</div>
            <div className="text-xs text-slate-500 mt-1 truncate">{s.label}</div>
          </Card>
        ))}
      </div>

      <section className="mb-6">
        <h2 className="text-lg font-bold text-[#16233A] mb-3">{t("provider.quickActions")}</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {QUICK.map((q) => (
            <Link key={q.key} to={q.to} data-testid={`quick-${q.key}`}>
              <Card className="!p-4 hover:border-[#F1701E] hover:bg-orange-50/30 transition-colors cursor-pointer">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-2 ${q.color}`}><q.icon className="w-5 h-5" /></div>
                <div className="text-sm font-semibold text-[#16233A]">{t(q.label)}</div>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section className="mb-6 min-w-0">
        <div className="flex items-center justify-between mb-3"><h2 className="text-lg font-bold text-[#16233A]">{t("provider.availableShipments")}</h2><Link to="/provider/available" className="text-sm text-[#F1701E] font-semibold">{t("common.view")}</Link></div>
        {state.opps.length === 0 ? <Card><EmptyState icon={Package} title={t("shipment.noShipments")} /></Card> : (
          <div className="grid gap-3 min-w-0">
            {state.opps.slice(0, 3).map((s) => (
              <Card key={s.id} data-testid={`dash-opp-${s.id}`} className="min-w-0 overflow-hidden">
                <div className="flex items-center justify-between gap-3 mb-2 min-w-0"><h3 className="min-w-0 truncate font-bold text-[#16233A]">{s.title}</h3><StatusBadge status={s.status} /></div>
                <RouteInline pickup={s.pickup_location} delivery={s.delivery_location} />
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="mb-6 min-w-0">
        <div className="flex items-center justify-between mb-3"><h2 className="text-lg font-bold text-[#16233A]">{t("provider.recentTransactions")}</h2><Link to="/provider/finance" className="text-sm text-[#F1701E] font-semibold">{t("common.view")}</Link></div>
        {state.txns.length === 0 ? <Card><EmptyState icon={Wallet} title={t("provider.noTransactions")} /></Card> : (
          <div className="grid gap-3 min-w-0">
            {state.txns.slice(0, 5).map((tx) => (
              <Card key={tx.id} className="!p-4 min-w-0 overflow-hidden">
                <div className="flex items-center justify-between gap-3 min-w-0"><span className="font-semibold text-[#16233A] truncate">{tx.description || tx.type}</span><span className="font-bold text-emerald-700 shrink-0">{fmt(tx.amount)}</span></div>
                <div className="text-xs text-slate-400 mt-1">{tx.created_at ? new Date(tx.created_at).toLocaleString() : "\u2014"}</div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="min-w-0">
        <h2 className="text-lg font-bold text-[#16233A] mb-3">{t("provider.recentActivity")}</h2>
        {state.notifs.length === 0 ? <Card><EmptyState icon={FileText} title={t("common.none")} /></Card> : (
          <div className="grid gap-3 min-w-0">
            {state.notifs.slice(0, 5).map((n) => (
              <Card key={n.id} className="!p-4 min-w-0 overflow-hidden">
                <div className="font-semibold text-[#16233A] truncate">{n.title_ar || n.title_en}</div>
                {(n.body_ar || n.body_en) && <div className="text-xs text-slate-500 mt-1">{n.body_ar || n.body_en}</div>}
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
