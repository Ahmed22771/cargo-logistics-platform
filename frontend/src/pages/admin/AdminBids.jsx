import React, { useEffect, useState } from "react";
import { Table } from "./AdminLayout";
import { Spinner, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

const BID_CLS = {
  PENDING: "bg-amber-50 text-amber-700 border-amber-200",
  ACCEPTED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  REJECTED: "bg-slate-100 text-slate-500 border-slate-200",
};

export default function AdminBids() {
  const { t, lang } = useI18n();
  const [rows, setRows] = useState(null);
  useEffect(() => { api.get("/admin/bids").then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  if (rows === null) return <Spinner label={t("common.loading")} />;
  return (
    <div>
      <PageHeader title={t("nav.bids")} />
      <Table testId="admin-bids-table" rows={rows}
        columns={[t("shipment.title"), t("trip.customer"), t("bid.driver"), t("bid.price"), t("common.status"), t("admin.timestamp")]}
        renderRow={(b) => (
          <tr key={b.id} data-testid={`admin-bid-${b.id}`} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A] max-w-[200px] truncate">{b.shipment_title}</td>
            <td className="px-4 py-3 text-slate-600">{b.customer_name}</td>
            <td className="px-4 py-3 text-slate-600">{b.driver_name}</td>
            <td className="px-4 py-3 font-bold text-[#F1701E]">{b.price} {t("common.currency")}</td>
            <td className="px-4 py-3"><span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold border ${BID_CLS[b.status]}`}>{t(`bid.${b.status === "ACCEPTED" ? "won" : b.status === "REJECTED" ? "lost" : "pending"}`)}</span></td>
            <td className="px-4 py-3 text-xs text-slate-400 font-mono">{new Date(b.created_at).toLocaleDateString(lang === "ar" ? "ar-OM" : "en-GB")}</td>
          </tr>
        )}
      />
    </div>
  );
}
