import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Package, Plus, Truck, CheckCircle2, Clock } from "lucide-react";
import { Card, Btn, Spinner, PageHeader } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";

export default function CustomerHome() {
  const { t } = useI18n();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [shipments, setShipments] = useState(null);

  useEffect(() => { api.get("/shipments/mine").then(({ data }) => setShipments(data)).catch(() => setShipments([])); }, []);

  if (shipments === null) return <Spinner label={t("common.loading")} />;

  const active = shipments.filter((s) => !["COMPLETED", "CANCELLED", "DRAFT"].includes(s.status));
  const completed = shipments.filter((s) => s.status === "COMPLETED");
  const stats = [
    { label: t("nav.myShipments"), value: shipments.length, icon: Package, color: "text-[#16233A] bg-[#16233A]/5" },
    { label: t("admin.activeShipments"), value: active.length, icon: Truck, color: "text-[#F1701E] bg-[#F1701E]/10" },
    { label: t("admin.completedShipments"), value: completed.length, icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50" },
  ];

  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={`${t("common.welcome")} ${user?.name} 👋`} subtitle={t("landing.customerCardDesc")}
        action={<Btn variant="accent" data-testid="home-create-shipment-btn" onClick={() => navigate("/customer/create")}><Plus className="w-4 h-4" /> {t("shipment.create")}</Btn>} />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-5 mb-8 min-w-0">
        {stats.map((s, i) => (
          <Card key={i} className="!p-4 md:!p-5 min-w-0 overflow-hidden">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${s.color}`}><s.icon className="w-5 h-5" /></div>
            <div className="text-2xl md:text-3xl font-extrabold text-[#16233A]">{s.value}</div>
            <div className="text-xs md:text-sm text-slate-500 mt-1 truncate">{s.label}</div>
          </Card>
        ))}
      </div>

      <h2 className="text-lg font-bold text-[#16233A] mb-3 flex items-center gap-2"><Clock className="w-5 h-5 text-[#F1701E]" /> {t("admin.activeShipments")}</h2>
      {active.length === 0 ? (
        <Card><p className="text-sm text-slate-400 text-center py-6">{t("shipment.noShipments")}</p></Card>
      ) : (
        <div className="grid gap-3">
          {active.map((s) => (
            <Card key={s.id} data-testid={`home-shipment-${s.id}`} className="!p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(`/customer/shipment/${s.id}`)}>
              <div className="flex items-center justify-between gap-3 mb-2">
                <h3 className="font-bold text-[#16233A] truncate">{s.title}</h3>
                <StatusBadge status={s.status} />
              </div>
              <RouteInline pickup={s.pickup_location} delivery={s.delivery_location} />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
