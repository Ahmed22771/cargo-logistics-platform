import React, { useEffect, useState } from "react";
import { Package, Truck, CheckCircle2, Clock, Users, Building2, ShieldCheck, Activity } from "lucide-react";
import { Card, Spinner, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function AdminDashboard() {
  const { t, lang } = useI18n();
  const [stats, setStats] = useState(null);
  useEffect(() => { api.get("/admin/stats").then(({ data }) => setStats(data)).catch(() => setStats({})); }, []);
  if (stats === null) return <Spinner label={t("common.loading")} />;

  const cards = [
    { label: t("admin.totalShipments"), value: stats.total_shipments, icon: Package, c: "text-[#16233A] bg-[#16233A]/5" },
    { label: t("admin.activeShipments"), value: stats.active_shipments, icon: Clock, c: "text-blue-600 bg-blue-50" },
    { label: t("admin.completedShipments"), value: stats.completed_shipments, icon: CheckCircle2, c: "text-emerald-600 bg-emerald-50" },
    { label: t("admin.activeTrips"), value: stats.active_trips, icon: Truck, c: "text-[#F1701E] bg-[#F1701E]/10" },
    { label: t("admin.totalDrivers"), value: stats.total_drivers, icon: Users, c: "text-[#16233A] bg-[#16233A]/5" },
    { label: t("admin.verifiedDrivers"), value: stats.verified_drivers, icon: ShieldCheck, c: "text-emerald-600 bg-emerald-50" },
    { label: t("admin.pendingVerification"), value: stats.pending_drivers, icon: Clock, c: "text-amber-600 bg-amber-50" },
    { label: t("admin.providers"), value: stats.providers, icon: Building2, c: "text-[#16233A] bg-[#16233A]/5" },
  ];

  return (
    <div>
      <PageHeader title={t("admin.dashboard")} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {cards.map((c, i) => (
          <Card key={i} data-testid={`admin-stat-${i}`} className="!p-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${c.c}`}><c.icon className="w-5 h-5" /></div>
            <div className="text-2xl md:text-3xl font-extrabold text-[#16233A]">{c.value ?? 0}</div>
            <div className="text-xs text-slate-500 mt-1">{c.label}</div>
          </Card>
        ))}
      </div>
      <Card>
        <h2 className="font-bold text-[#16233A] mb-4 flex items-center gap-2"><Activity className="w-5 h-5 text-[#F1701E]" /> {t("admin.recentActivity")}</h2>
        {(!stats.recent_activity || stats.recent_activity.length === 0) ? (
          <p className="text-sm text-slate-400 text-center py-4">{t("admin.noActivity")}</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {stats.recent_activity.map((a) => (
              <div key={a.id} className="py-2.5 flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-700 font-medium">{a.admin_name} · {a.action}</span>
                <span className="text-xs text-slate-400 font-mono">{new Date(a.timestamp).toLocaleString(lang === "ar" ? "ar-OM" : "en-GB")}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
