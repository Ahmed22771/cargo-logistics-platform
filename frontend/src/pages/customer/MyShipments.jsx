import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Package, Plus } from "lucide-react";
import { Card, Btn, Spinner, PageHeader, EmptyState } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function MyShipments() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [shipments, setShipments] = useState(null);

  useEffect(() => { api.get("/shipments/mine").then(({ data }) => setShipments(data)).catch(() => setShipments([])); }, []);

  if (shipments === null) return <Spinner label={t("common.loading")} />;

  return (
    <div>
      <PageHeader title={t("nav.myShipments")}
        action={<Btn variant="accent" data-testid="create-shipment-btn" onClick={() => navigate("/customer/create")}><Plus className="w-4 h-4" /> {t("shipment.create")}</Btn>} />
      {shipments.length === 0 ? (
        <Card><EmptyState icon={Package} title={t("shipment.noShipments")} subtitle={t("shipment.createFirst")}
          action={<Btn variant="accent" onClick={() => navigate("/customer/create")}><Plus className="w-4 h-4" /> {t("shipment.create")}</Btn>} /></Card>
      ) : (
        <div className="grid gap-3">
          {shipments.map((s) => (
            <Card key={s.id} data-testid={`shipment-card-${s.id}`} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(`/customer/shipment/${s.id}`)}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0">
                  <h3 className="font-bold text-[#16233A] truncate">{s.title}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">{s.category} · {s.weight} {t("common.km") === "km" ? "kg" : "كجم"}</p>
                </div>
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
