import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Package,
  Gavel,
  CheckCircle2,
  Edit3,
} from "lucide-react";
import {
  Card,
  Spinner,
  PageHeader,
  EmptyState,
  Btn,
  Field,
  Input,
  Textarea,
} from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteDisplay } from "../../components/RouteDisplay";
import { vehicleTypeLabel } from "../../lib/vehicleTypes";
import { VerificationBanner } from "./VerificationBanner";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api, { apiErr, eligibilityError } from "../../lib/api";

function BidModal({ shipment, onClose, onSubmitted }) {
  const { t, lang } = useI18n();

  const customerPrice = Number(shipment?.customer_max_offer);

  const hasCustomerPrice =
    shipment?.customer_max_offer != null &&
    Number.isFinite(customerPrice) &&
    customerPrice > 0;

  const [priceMode, setPriceMode] = useState(
    hasCustomerPrice ? "customer" : "custom"
  );

  const [price, setPrice] = useState(
    hasCustomerPrice ? String(customerPrice) : ""
  );

  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const currency =
    shipment?.pricing_currency || t("common.currency");

  const selectCustomerPrice = () => {
    if (!hasCustomerPrice || busy) return;

    setPriceMode("customer");
    setPrice(String(customerPrice));
  };

  const selectCustomPrice = () => {
    if (busy) return;

    setPriceMode("custom");
    setPrice("");
  };

  const submit = async () => {
    if (busy) return;

    let p;

    // الحالة الأولى:
    // الموافقة على سعر العميل
    if (priceMode === "customer") {
      if (!hasCustomerPrice) {
        toast.error(
          t(
            "bid.customerPriceUnavailable",
            lang === "ar"
              ? "سعر العميل غير متاح لهذه الشحنة."
              : "The customer's price is not available for this shipment."
          )
        );
        return;
      }

      p = customerPrice;
    }

    // الحالة الثانية:
    // السائق يحدد سعرًا مختلفًا
    else {
      p = parseFloat(price);

      if (!p || p <= 0) {
        toast.error(t("bid.priceRequired"));
        return;
      }
    }

    setBusy(true);

    try {
      await api.post(`/shipments/${shipment.id}/bids`, {
        price: p,
        note,
      });

      toast.success(t("bid.submitted"));

      onSubmitted();
    } catch (e) {
      const elig = eligibilityError(e);

      if (elig) {
        const detail = (elig.reasons || [])
          .map((r) =>
            t(
              `bid.eligibilityReasons.${r?.code}`,
              r?.message || ""
            )
          )
          .filter(Boolean)
          .join(" • ");

        toast.error(
          detail
            ? `${t("bid.notEligible")}: ${detail}`
            : t("bid.notEligible")
        );
      } else {
        toast.error(apiErr(e));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="bid-modal"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="absolute inset-0 bg-black/50"
        data-testid="bid-modal-overlay"
        onClick={onClose}
      />

      <div
        className="relative flex max-h-[90vh] w-full max-w-md flex-col overflow-hidden rounded-2xl bg-white shadow-xl animate-fade-in"
        onClick={(e) => e.stopPropagation()}
        dir={lang === "ar" ? "rtl" : "ltr"}
      >
        {/* Header */}
        <div className="shrink-0 p-6 pb-3">
          <h2 className="mb-1 text-lg font-bold text-[#16233A]">
            {t("bid.submit")}
          </h2>

          <p className="line-clamp-2 text-sm text-slate-400">
            {shipment.title}
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6">
          <div className="space-y-4">

            {/* Customer Price */}
            {hasCustomerPrice && (
              <div
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
                data-testid="bid-customer-price"
              >
                <span className="text-slate-500">
                  {t(
                    "bid.customerPrice",
                    lang === "ar"
                      ? "سعر العميل"
                      : "Customer price"
                  )}
                  :{" "}
                </span>

                <span className="font-bold text-[#F1701E]">
                  {customerPrice} {currency}
                </span>
              </div>
            )}

            {/* Offer Type */}
            <div className="space-y-3">
              <p className="text-sm font-semibold text-[#16233A]">
                {t(
                  "bid.chooseOfferType",
                  lang === "ar"
                    ? "كيف تريد تقديم عرضك؟"
                    : "How would you like to submit your offer?"
                )}
              </p>

              {/* Option 1: Accept Customer Price */}
              {hasCustomerPrice && (
                <button
                  type="button"
                  data-testid="bid-customer-price-option"
                  onClick={selectCustomerPrice}
                  disabled={busy}
                  className={`flex w-full items-start gap-3 rounded-xl border p-4 text-start transition ${
                    priceMode === "customer"
                      ? "border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                  } disabled:cursor-not-allowed disabled:opacity-60`}
                >
                  <span
                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                      priceMode === "customer"
                        ? "border-emerald-600 bg-emerald-600 text-white"
                        : "border-slate-300 bg-white"
                    }`}
                  >
                    {priceMode === "customer" && (
                      <CheckCircle2 size={14} />
                    )}
                  </span>

                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="font-bold text-slate-800">
                      {t(
                        "bid.acceptCustomerPrice",
                        lang === "ar"
                          ? "الموافقة على سعر العميل"
                          : "Accept customer price"
                      )}
                    </span>

                    <span className="mt-1 text-sm text-slate-500">
                      {customerPrice} {currency}
                    </span>
                  </span>
                </button>
              )}

              {/* Option 2: Different Price */}
              <button
                type="button"
                data-testid="bid-custom-price-option"
                onClick={selectCustomPrice}
                disabled={busy}
                className={`flex w-full items-start gap-3 rounded-xl border p-4 text-start transition ${
                  priceMode === "custom"
                    ? "border-[#F1701E] bg-orange-50 ring-1 ring-[#F1701E]"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                } disabled:cursor-not-allowed disabled:opacity-60`}
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                    priceMode === "custom"
                      ? "border-[#F1701E] bg-[#F1701E] text-white"
                      : "border-slate-300 bg-white"
                  }`}
                >
                  {priceMode === "custom" && (
                    <CheckCircle2 size={14} />
                  )}
                </span>

                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="inline-flex items-center gap-2 font-bold text-slate-800">
                    <Edit3 size={16} />

                    {t(
                      "bid.submitDifferentPrice",
                      lang === "ar"
                        ? "تقديم عرض بسعر مختلف"
                        : "Submit a different price"
                    )}
                  </span>

                  <span className="mt-1 text-sm text-slate-500">
                    {t(
                      "bid.driverSetsPrice",
                      lang === "ar"
                        ? "السائق يحدد السعر الذي يريد تقديمه."
                        : "The driver sets the price for the offer."
                    )}
                  </span>
                </span>
              </button>
            </div>

            {/* Custom Price Input */}
            {priceMode === "custom" && (
              <Field
                label={t(
                  "bid.price",
                  lang === "ar"
                    ? "السعر الذي تقدمه"
                    : "Your offer price"
                )}
                required
                hint={t("bid.enterPrice")}
              >
                <Input
                  type="number"
                  min="0.001"
                  step="0.001"
                  data-testid="bid-price-input"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="force-ltr"
                  placeholder="0.000"
                  disabled={busy}
                />
              </Field>
            )}

            {/* Selected Customer Price */}
            {priceMode === "customer" &&
              hasCustomerPrice && (
                <div
                  className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3"
                  data-testid="bid-selected-customer-price"
                >
                  <div className="text-xs font-medium text-emerald-700">
                    {t(
                      "bid.selectedPrice",
                      lang === "ar"
                        ? "السعر المعتمد للعرض"
                        : "Offer price"
                    )}
                  </div>

                  <div className="mt-1 text-lg font-bold text-emerald-800">
                    {customerPrice} {currency}
                  </div>
                </div>
              )}

            {/* Note */}
            <Field label={t("bid.note")}>
              <Textarea
                rows={2}
                data-testid="bid-note-input"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                disabled={busy}
              />
            </Field>
          </div>
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t border-slate-100 p-6 pt-3">
          <div className="flex gap-2">
            <Btn
              variant="secondary"
              onClick={onClose}
              disabled={busy}
              data-testid="cancel-bid-btn"
              className="flex-1 justify-center"
            >
              {t("common.cancel")}
            </Btn>

            <Btn
              variant="accent"
              onClick={submit}
              disabled={busy}
              data-testid="submit-bid-btn"
              className="flex-1 justify-center"
            >
              <Gavel className="h-4 w-4" />

              {t(
                "bid.confirmOffer",
                lang === "ar"
                  ? "تأكيد العرض"
                  : "Confirm offer"
              )}
            </Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AvailableShipments() {
  const { t } = useI18n();
  const { user } = useAuth();

  const [shipments, setShipments] = useState(null);
  const [modal, setModal] = useState(null);

  const approved =
    user?.verification_status === "APPROVED";

  const load = () => {
    if (!approved) {
      setShipments([]);
      return;
    }

    api
      .get("/marketplace/shipments")
      .then(({ data }) => setShipments(data))
      .catch(() => setShipments([]));
  };

  useEffect(load, [approved]);

  if (shipments === null) {
    return (
      <Spinner label={t("common.loading")} />
    );
  }

  return (
    <div>
      <PageHeader
        title={t("nav.availableShipments")}
      />

      <VerificationBanner />

      {!approved ? null : shipments.length === 0 ? (
        <Card>
          <EmptyState
            icon={Package}
            title={t("shipment.noShipments")}
          />
        </Card>
      ) : (
        <div className="grid gap-3">
          {shipments.map((s) => (
            <Card
              key={s.id}
              data-testid={`available-${s.id}`}
            >
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-[#16233A]">
                    {s.title}
                  </h3>

                  <p className="mt-0.5 text-xs text-slate-400">
                    {s.category} · {s.weight} kg ·{" "}
                    {vehicleTypeLabel(
                      t,
                      s.vehicle_type
                    )}
                  </p>
                </div>

                <StatusBadge status={s.status} />
              </div>

              <RouteDisplay
                pickup={s.pickup_location}
                delivery={s.delivery_location}
              />

              {/* Customer Price */}
              {s.customer_max_offer != null && (
                <div
                  className="mt-3 text-sm text-slate-500"
                  data-testid={`max-offer-${s.id}`}
                >
                  {t(
                    "shipment.customerMaxOffer"
                  )}
                  :{" "}
                  <span className="font-bold text-[#F1701E]">
                    {s.customer_max_offer}{" "}
                    {s.pricing_currency ||
                      t("common.currency")}
                  </span>
                </div>
              )}

              {/* Advisory Price */}
              {s.advisory_price != null && (
                <div className="mt-1 text-xs text-slate-400">
                  {t(
                    "shipment.advisoryPrice"
                  )}
                  :{" "}
                  {s.advisory_price}{" "}
                  {s.pricing_currency ||
                    t("common.currency")}
                </div>
              )}

              <div className="mt-4">
                {s.already_bid ? (
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-emerald-600">
                    <Gavel className="h-4 w-4" />

                    {t("bid.alreadyBid")}
                  </div>
                ) : (
                  <Btn
                    variant="accent"
                    data-testid={`bid-btn-${s.id}`}
                    onClick={() => setModal(s)}
                    className="w-full sm:w-auto"
                  >
                    <Gavel className="h-4 w-4" />

                    {t("bid.submit")}
                  </Btn>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {modal && (
        <BidModal
          shipment={modal}
          onClose={() => setModal(null)}
          onSubmitted={() => {
            setModal(null);
            load();
          }}
        />
      )}
    </div>
  );
}