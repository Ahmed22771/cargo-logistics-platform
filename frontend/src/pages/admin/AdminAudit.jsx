import React, { useEffect, useState } from "react";
import { Table } from "./AdminLayout";
import { Spinner, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function AdminAudit() {
  const { t, lang } = useI18n();
  const [rows, setRows] = useState(null);
  useEffect(() => { api.get("/admin/audit-logs").then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  if (rows === null) return <Spinner label={t("common.loading")} />;
  return (
    <div>
      <PageHeader title={t("nav.auditLog")} />
      <Table testId="admin-audit-table" rows={rows}
        columns={["Admin", t("admin.action"), t("admin.entity"), "ID", t("admin.result"), t("admin.timestamp")]}
        renderRow={(a) => (
          <tr key={a.id} data-testid={`audit-row-${a.id}`} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A]">{a.admin_name}</td>
            <td className="px-4 py-3 text-slate-600 font-mono text-xs">{a.action}</td>
            <td className="px-4 py-3 text-slate-500">{a.entity}</td>
            <td className="px-4 py-3 font-mono text-xs text-slate-400 max-w-[120px] truncate force-ltr">{a.entity_id}</td>
            <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700">{a.result}</span></td>
            <td className="px-4 py-3 text-xs text-slate-400 font-mono">{new Date(a.timestamp).toLocaleString(lang === "ar" ? "ar-OM" : "en-GB")}</td>
          </tr>
        )}
      />
    </div>
  );
}
