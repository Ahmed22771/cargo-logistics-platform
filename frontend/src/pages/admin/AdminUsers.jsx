import React, { useEffect, useState } from "react";
import { Table } from "./AdminLayout";
import { Spinner, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

const ROLE_CLS = {
  admin: "bg-[#16233A] text-white",
  customer: "bg-blue-50 text-blue-700 border border-blue-200",
  driver: "bg-orange-50 text-orange-700 border border-orange-200",
  provider: "bg-emerald-50 text-emerald-700 border border-emerald-200",
};

export default function AdminUsers() {
  const { t, lang } = useI18n();
  const [rows, setRows] = useState(null);
  useEffect(() => { api.get("/admin/users").then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  if (rows === null) return <Spinner label={t("common.loading")} />;
  const roleLabel = { admin: "Admin", customer: t("auth.customer"), driver: t("auth.driver"), provider: t("auth.provider") };
  return (
    <div>
      <PageHeader title={t("nav.users")} />
      <Table testId="admin-users-table" rows={rows}
        columns={[t("auth.name"), t("common.status"), t("auth.phone"), t("auth.email")]}
        renderRow={(u) => (
          <tr key={u.id} data-testid={`admin-user-${u.id}`} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A]">{u.name}</td>
            <td className="px-4 py-3"><span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold ${ROLE_CLS[u.role]}`}>{roleLabel[u.role]}</span></td>
            <td className="px-4 py-3 font-mono text-xs force-ltr">{u.phone || "—"}</td>
            <td className="px-4 py-3 text-slate-500 force-ltr">{u.email || "—"}</td>
          </tr>
        )}
      />
    </div>
  );
}
