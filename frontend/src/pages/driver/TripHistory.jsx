import React, { useEffect, useState } from "react";
import { History } from "lucide-react";
import { Card, Spinner, PageHeader, EmptyState } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function TripHistory() {
  const { t } = useI18n();
  const [trips, setTrips] = useState(null);
  useEffect(() => { api.get("/trips/mine").then(({ data }) => setTrips(data.filter((tr) => ["COMPLETED", "DELIVERED"].includes(tr.status)))).catch(() => setTrips([])); }, []);
  if (trips === null) return <Spinner label={t("common.loading")} />;
  return (
    <div>
      <PageHeader title={t("trip.history")} />
      {trips.length === 0 ? (
        <Card><EmptyState icon={History} title={t("trip.noHistory")} /></Card>
      ) : (
        <div className="grid gap-3">
          {trips.map((tr) => (
            <Card key={tr.id} data-testid={`history-${tr.id}`}>
              <div className="flex items-center justify-between gap-3 mb-2"><h3 className="font-bold text-[#16233A]">{tr.shipment_title}</h3><StatusBadge status={tr.status} /></div>
              <RouteInline pickup={tr.pickup_location} delivery={tr.delivery_location} />
              <div className="mt-2 text-sm">{t("common.price")}: <span className="font-bold text-[#F1701E]">{tr.price} {t("common.currency")}</span></div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
