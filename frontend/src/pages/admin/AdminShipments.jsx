import React, { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { Table } from "./AdminLayout";
import { Spinner, PageHeader, Input } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function AdminShipments() {
  const { t } = useI18n();
  const [rows, setRows] = useState(null);
  const [q, setQ] = useState("");
  useEffect(() => { api.get("/admin/shipments").then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  if (rows === null) return <Spinner label={t("common.loading")} />;
  const filtered = rows.filter((s) => s.title?.toLowerCase().includes(q.toLowerCase()) || s.customer_name?.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <PageHeader title={t("nav.shipments")} />
      <div className="relative mb-4 max-w-sm">
        <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
        <Input data-testid="shipment-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("common.search")} className="ps-9" />
      </div>
      <Table testId="admin-shipments-table" rows={filtered}
        columns={[t("shipment.title"), t("trip.customer"), t("common.from"), t("common.to"), t("common.status")]}
        renderRow={(s) => (
          <tr key={s.id} data-testid={`admin-shipment-${s.id}`} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A] max-w-[220px] truncate">{s.title}</td>
            <td className="px-4 py-3 text-slate-600">{s.customer_name}</td>
            <td className="px-4 py-3 text-slate-500 max-w-[160px] truncate">{s.pickup_location?.address || "—"}</td>
            <td className="px-4 py-3 text-slate-500 max-w-[160px] truncate">{s.delivery_location?.address || "—"}</td>
            <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
          </tr>
        )}
      />
    </div>
  );
}
