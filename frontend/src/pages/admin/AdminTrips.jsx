import React, { useEffect, useState } from "react";
import { Table } from "./AdminLayout";
import { Spinner, PageHeader } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function AdminTrips() {
  const { t } = useI18n();
  const [rows, setRows] = useState(null);
  useEffect(() => { api.get("/admin/trips").then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  if (rows === null) return <Spinner label={t("common.loading")} />;
  return (
    <div>
      <PageHeader title={t("nav.trips")} />
      <Table testId="admin-trips-table" rows={rows}
        columns={[t("shipment.title"), t("trip.customer"), t("bid.driver"), t("common.from"), t("common.to"), t("common.status")]}
        renderRow={(tr) => (
          <tr key={tr.id} data-testid={`admin-trip-${tr.id}`} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A] max-w-[200px] truncate">{tr.shipment_title}</td>
            <td className="px-4 py-3 text-slate-600">{tr.customer_name}</td>
            <td className="px-4 py-3 text-slate-600">{tr.driver_name}</td>
            <td className="px-4 py-3 text-slate-500 max-w-[150px] truncate">{tr.pickup_location?.address || "—"}</td>
            <td className="px-4 py-3 text-slate-500 max-w-[150px] truncate">{tr.delivery_location?.address || "—"}</td>
            <td className="px-4 py-3"><StatusBadge status={tr.status} /></td>
          </tr>
        )}
      />
    </div>
  );
}
