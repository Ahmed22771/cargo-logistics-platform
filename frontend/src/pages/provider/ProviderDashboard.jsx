import React, { useEffect, useState } from "react";
import { Building2, Package, Truck, MapPin } from "lucide-react";
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
  useEffect(() => {
    api.get("/provider/summary").then(({ data }) => setSummary(data)).catch(() => setSummary({}));
    api.get("/provider/opportunities").then(({ data }) => setOpps(data)).catch(() => setOpps([]));
  }, []);
  if (summary === null) return <Spinner label={t("common.loading")} />;
  const stats = [
    { label: t("nav.opportunities"), value: summary.opportunities || 0, icon: Package, color: "text-[#F1701E] bg-[#F1701E]/10" },
    { label: t("nav.trips"), value: summary.trips || 0, icon: Truck, color: "text-[#16233A] bg-[#16233A]/5" },
  ];
  return (
    <div>
      <PageHeader title={user?.company_name || t("nav.dashboard")} subtitle={<span className="flex items-center gap-1"><Building2 className="w-4 h-4" /> {user?.name}</span>} />
      <div className="grid grid-cols-2 gap-4 mb-6 max-w-md">
        {stats.map((s, i) => (
          <Card key={i} className="!p-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${s.color}`}><s.icon className="w-5 h-5" /></div>
            <div className="text-3xl font-extrabold text-[#16233A]">{s.value}</div>
            <div className="text-sm text-slate-500 mt-1">{s.label}</div>
          </Card>
        ))}
      </div>
      {user?.service_areas?.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {user.service_areas.map((a, i) => <span key={i} className="inline-flex items-center gap-1 bg-slate-100 rounded-full px-3 py-1 text-sm text-slate-600"><MapPin className="w-3.5 h-3.5 text-[#F1701E]" /> {a}</span>)}
        </div>
      )}
      <h2 className="text-lg font-bold text-[#16233A] mb-3">{t("nav.opportunities")}</h2>
      {opps.length === 0 ? (
        <Card><EmptyState icon={Package} title={t("shipment.noShipments")} /></Card>
      ) : (
        <div className="grid gap-3">
          {opps.map((s) => (
            <Card key={s.id} data-testid={`opp-${s.id}`}>
              <div className="flex items-center justify-between gap-3 mb-2"><h3 className="font-bold text-[#16233A]">{s.title}</h3><StatusBadge status={s.status} /></div>
              <RouteInline pickup={s.pickup_location} delivery={s.delivery_location} />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
