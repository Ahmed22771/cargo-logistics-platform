import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Gavel } from "lucide-react";
import { Card, Spinner, EmptyState, PageHeader } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

const TABS = [
  { key: "ALL", label: "common.all" },
  { key: "PENDING", label: "status.PENDING" },
  { key: "ACCEPTED", label: "status.ACCEPTED" },
  { key: "REJECTED", label: "status.REJECTED" },
  { key: "CANCELLED", label: "status.CANCELLED" },
];

export default function ProviderOffers() {
  const { t } = useI18n();
  const [bids, setBids] = useState(null);
  const [tab, setTab] = useState("ALL");
  useEffect(() => { api.get("/provider/bids").then(({ data }) => setBids(data)).catch(() => setBids([])); }, []);
  const filtered = useMemo(() => (bids || []).filter((b) => tab === "ALL" || b.status === tab), [bids, tab]);
  if (bids === null) return <Spinner label={t("common.loading")} />;
  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={t("provider.offers")} />
      <div className="flex flex-wrap gap-2 mb-4">
        {TABS.map((tab_) => (
          <button key={tab_.key} data-testid={`offers-tab-${tab_.key}`} onClick={() => setTab(tab_.key)}
            className={`px-3 py-1.5 rounded-lg text-sm font-semibold border ${tab === tab_.key ? "bg-[#16233A] text-white border-[#16233A]" : "bg-white text-slate-600 border-slate-200 hover:border-[#F1701E]"}`}>
            {t(tab_.label) || tab_.key}
          </button>
        ))}
      </div>
      {filtered.length === 0 ? <Card><EmptyState icon={Gavel} title={t("provider.noBids")} /></Card> : (
        <div className="grid gap-3">
          {filtered.map((b) => (
            <Card key={b.id} data-testid={`offer-${b.id}`} className="min-w-0 overflow-hidden">
              <div className="flex items-center justify-between gap-3 min-w-0">
                <h3 className="font-bold text-[#16233A] truncate">{b.shipment?.title || b.shipment_id}</h3>
                <StatusBadge status={b.status} />
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2 text-sm text-slate-600">
                <div><span className="text-slate-400">{t("provider.amount")}:</span> <b>{b.price} {t("common.currency")}</b></div>
                <div><span className="text-slate-400">{t("provider.date")}:</span> {b.created_at ? new Date(b.created_at).toLocaleDateString() : "\u2014"}</div>
                {b.driver_name && <div className="col-span-2 text-slate-500">{t("shipment.driver") || t("nav.drivers")}: {b.driver_name}</div>}
              </div>
              {b.status === "ACCEPTED" && b.shipment?.trip_id && (
                <div className="mt-3">
                  <Link to={`/provider/trips/${b.shipment.trip_id}`} className="text-sm font-semibold text-[#F1701E]">{t("provider.tripHistory")} \u2192</Link>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
