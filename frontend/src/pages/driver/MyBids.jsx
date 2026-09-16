import React, { useEffect, useState } from "react";
import { Gavel } from "lucide-react";
import { Card, Spinner, PageHeader, EmptyState } from "../../components/ui-kit";
import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

const BID_STATUS = {
  PENDING: { key: "bid.pending", cls: "bg-amber-50 text-amber-700 border-amber-200" },
  ACCEPTED: { key: "bid.won", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  REJECTED: { key: "bid.lost", cls: "bg-slate-100 text-slate-500 border-slate-200" },
};

export default function MyBids() {
  const { t } = useI18n();
  const [bids, setBids] = useState(null);
  useEffect(() => { api.get("/driver/bids").then(({ data }) => setBids(data)).catch(() => setBids([])); }, []);
  if (bids === null) return <Spinner label={t("common.loading")} />;
  return (
    <div>
      <PageHeader title={t("nav.myBids")} />
      {bids.length === 0 ? (
        <Card><EmptyState icon={Gavel} title={t("shipment.noBidsYet")} /></Card>
      ) : (
        <div className="grid gap-3">
          {bids.map((b) => {
            const st = BID_STATUS[b.status] || BID_STATUS.PENDING;
            return (
              <Card key={b.id} data-testid={`mybid-${b.id}`}>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h3 className="font-bold text-[#16233A]">{b.shipment?.title || "—"}</h3>
                  <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold border ${st.cls}`}>{t(st.key)}</span>
                </div>
                {b.shipment && <RouteInline pickup={b.shipment.pickup_location} delivery={b.shipment.delivery_location} />}
                <div className="mt-2 text-sm">{t("bid.price")}: <span className="font-bold text-[#F1701E]">{b.price} {t("common.currency")}</span></div>
                {b.note && <p className="text-sm text-slate-500 mt-1">{b.note}</p>}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
