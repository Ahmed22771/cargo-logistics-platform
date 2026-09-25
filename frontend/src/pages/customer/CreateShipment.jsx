import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Check, Image as ImageIcon, X, MapPin, Calendar, Package2, Truck, Wallet } from "lucide-react";
import { Card, Btn, Field, Input, Textarea } from "../../components/ui-kit";
import { MapPicker } from "../../components/MapPicker";
import { RouteDisplay } from "../../components/RouteDisplay";
import { VEHICLE_TYPES } from "../../lib/vehicleTypes";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

export default function CreateShipment() {
  const { t, isRTL } = useI18n();
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    title: "",
    images: [],
    vehicle_type: "",
    fragile: false,
    loading_service: false,
    unloading_service: false,
    pickup_location: null,
    delivery_location: null,
    pickup_date: "",
    pickup_time: "",
    delivery_date: "",
    delivery_time: "",
  });
  const [pricing, setPricing] = useState(null); // {advisory_price, pricing_min, pricing_max, pricing_currency}
  const [maxOffer, setMaxOffer] = useState(null);
  const set = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  // Advisory pricing preview — recomputed server-side whenever the pricing
  // inputs change (vehicle type + both locations). The map logic is untouched.
  useEffect(() => {
    if (!form.vehicle_type || !form.pickup_location || !form.delivery_location) {
      setPricing(null);
      return;
    }
    let cancelled = false;
    api
      .post("/pricing/quote", {
        pickup_location: form.pickup_location,
        delivery_location: form.delivery_location,
        vehicle_type: form.vehicle_type,
        fragile: form.fragile,
        loading_service: form.loading_service,
        unloading_service: form.unloading_service,
      })
      .then(({ data }) => {
        if (cancelled) return;
        setPricing(data);
        setMaxOffer(data.advisory_price); // default the slider to the advisory price
      })
      .catch(() => { if (!cancelled) setPricing(null); });
    return () => { cancelled = true; };
  }, [form.vehicle_type, form.pickup_location, form.delivery_location, form.fragile, form.loading_service, form.unloading_service]);

  const handlePhoto = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => set("images", [reader.result]);
    reader.readAsDataURL(file);
  };

  const removePhoto = () => set("images", []);

  const submit = async () => {
    const description = form.title.trim();
    if (!description) {
      toast.error(t("shipment.titleRequired"));
      return;
    }
    if (!form.pickup_location && !form.delivery_location) {
      toast.error(t("shipment.missingBoth"));
      return;
    }
    if (!form.pickup_location) {
      toast.error(t("shipment.missingPickup"));
      return;
    }
    if (!form.delivery_location) {
      toast.error(t("shipment.missingDelivery"));
      return;
    }
    if (!form.vehicle_type) {
      toast.error(t("shipment.selectVehicleType"));
      return;
    }
    setSaving(true);
    try {
      await api.post("/shipments", {
        title: description,
        description,
        images: form.images,
        fragile: form.fragile,
        pickup_location: form.pickup_location,
        delivery_location: form.delivery_location,
        pickup_date: form.pickup_date,
        pickup_time: form.pickup_time,
        delivery_date: form.delivery_date,
        delivery_time: form.delivery_time,
        vehicle_type: form.vehicle_type,
        required_capacity: "",
        loading_service: form.loading_service,
        unloading_service: form.unloading_service,
        expected_price: "",
        customer_max_offer: maxOffer,
        status: "PUBLISHED",
      });
      toast.success(t("shipment.publishedSuccess"));
      navigate("/customer/shipments");
    } catch (error) {
      const code = apiErr(error);
      const messages = {
        MISSING_PICKUP: t("shipment.missingPickup"),
        MISSING_DELIVERY: t("shipment.missingDelivery"),
        MISSING_BOTH: t("shipment.missingBoth"),
      };
      toast.error(messages[code] || code);
    } finally {
      setSaving(false);
    }
  };

  const serviceLabels = {
    fragile: t("p11.wiz.fragile"),
    loading_service: t("shipment.loadingService"),
    unloading_service: t("shipment.unloadingService"),
  };
  const selectedServices = Object.keys(serviceLabels)
    .filter((key) => form[key])
    .map((key) => serviceLabels[key]);

  return (
    <div className="max-w-2xl mx-auto pb-8">
      <button
        onClick={() => navigate("/customer/shipments")}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"
        data-testid="back-to-shipments"
      >
        <ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} /> {t("nav.myShipments")}
      </button>
      <h1 className="text-2xl font-extrabold text-[#16233A] mb-5">{t("shipment.create")}</h1>

      <div className="space-y-4">
        {/* 1. What to ship — single description field + optional photo */}
        <Card data-testid="section-what">
          <div className="flex items-center gap-2 mb-3">
            <Package2 className="w-5 h-5 text-[#F1701E]" />
            <h2 className="font-bold text-base text-[#16233A]">{t("shipment.simpleTitle")}</h2>
          </div>
          <Field label={t("shipment.description")}>
            <Textarea
              data-testid="ship-title"
              rows={3}
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
              placeholder={t("shipment.cargoPlaceholder")}
            />
          </Field>
          <div className="mt-3">
            {form.images.length === 0 ? (
              <label
                className="flex items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl p-4 cursor-pointer hover:border-[#F1701E] transition-colors"
                data-testid="photo-upload-label"
              >
                <ImageIcon className="w-5 h-5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-600">
                  {t("shipment.addPhotoOptional")}
                </span>
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  data-testid="photo-input"
                  onChange={handlePhoto}
                />
              </label>
            ) : (
              <div className="relative w-32 h-32 rounded-lg overflow-hidden border border-slate-200">
                <img src={form.images[0]} alt="" className="w-full h-full object-cover" />
                <button
                  type="button"
                  data-testid="remove-photo"
                  onClick={removePhoto}
                  className="absolute top-1 end-1 bg-black/60 text-white rounded-full p-1"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

          {/* Required vehicle type — directly after the shipment description */}
          <div className="mt-4">
            <Field label={t("shipment.requiredVehicleType")}>
              <select
                data-testid="ship-vehicle-type"
                value={form.vehicle_type}
                onChange={(e) => set("vehicle_type", e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 focus:border-[#F1701E] focus:outline-none focus:ring-1 focus:ring-[#F1701E]"
              >
                <option value="">{t("shipment.selectVehicleType")}</option>
                {VEHICLE_TYPES.map((v) => (
                  <option key={v.value} value={v.value}>{t(v.labelKey)}</option>
                ))}
              </select>
            </Field>
          </div>
        </Card>

        {/* 2. From where — pickup map */}
        <Card data-testid="section-from">
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="w-5 h-5 text-[#F1701E]" />
            <h2 className="font-bold text-base text-[#16233A]">{t("shipment.fromTitle")}</h2>
          </div>
          <MapPicker
            testIdPrefix="pickup-map"
            value={form.pickup_location}
            confirmLabel={t("shipment.confirmPickup")}
            onConfirm={(loc) => {
              set("pickup_location", loc);
              toast.success(t("shipment.confirmPickup"));
            }}
          />
          {form.pickup_location && (
            <div
              className="text-sm text-emerald-600 font-semibold flex items-center gap-1.5 mt-2"
              data-testid="pickup-confirmed"
            >
              <Check className="w-4 h-4" />
              {form.pickup_location.address || t("p11.map.unnamed")}
            </div>
          )}
        </Card>

        {/* 3. To where — delivery map */}
        <Card data-testid="section-to">
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="w-5 h-5 text-[#16233A]" />
            <h2 className="font-bold text-base text-[#16233A]">{t("shipment.toTitle")}</h2>
          </div>
          <MapPicker
            testIdPrefix="delivery-map"
            value={form.delivery_location}
            accentConfirm={false}
            confirmLabel={t("shipment.confirmDelivery")}
            onConfirm={(loc) => {
              set("delivery_location", loc);
              toast.success(t("shipment.confirmDelivery"));
            }}
          />
          {form.delivery_location && (
            <div
              className="text-sm text-emerald-600 font-semibold flex items-center gap-1.5 mt-2"
              data-testid="delivery-confirmed"
            >
              <Check className="w-4 h-4" />
              {form.delivery_location.address || t("p11.map.unnamed")}
            </div>
          )}
        </Card>

        {/* 4. When — combined load and delivery date/time */}
        <Card data-testid="section-when">
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-5 h-5 text-[#F1701E]" />
            <h2 className="font-bold text-base text-[#16233A]">{t("shipment.schedule")}</h2>
          </div>
          <div className="space-y-3">
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-1.5">
                {t("shipment.pickupWhen")}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("shipment.pickupDate")}>
                  <Input
                    type="date"
                    data-testid="ship-pickup-date"
                    value={form.pickup_date}
                    onChange={(e) => set("pickup_date", e.target.value)}
                    className="force-ltr"
                  />
                </Field>
                <Field label={t("common.time")}>
                  <Input
                    type="time"
                    data-testid="ship-pickup-time"
                    value={form.pickup_time}
                    onChange={(e) => set("pickup_time", e.target.value)}
                    className="force-ltr"
                  />
                </Field>
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-1.5">
                {t("shipment.deliveryWhen")}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("shipment.deliveryDate")}>
                  <Input
                    type="date"
                    data-testid="ship-delivery-date"
                    value={form.delivery_date}
                    onChange={(e) => set("delivery_date", e.target.value)}
                    className="force-ltr"
                  />
                </Field>
                <Field label={t("common.time")}>
                  <Input
                    type="time"
                    data-testid="ship-delivery-time"
                    value={form.delivery_time}
                    onChange={(e) => set("delivery_time", e.target.value)}
                    className="force-ltr"
                  />
                </Field>
              </div>
            </div>
          </div>
        </Card>

        {/* 5. Extra services — 3 checkboxes only */}
        <Card data-testid="section-services">
          <h2 className="font-bold text-base text-[#16233A] mb-3">
            {t("shipment.servicesTitle")}
          </h2>
          <div className="flex flex-row flex-wrap gap-4">
            {[
              ["fragile", t("p11.wiz.fragile")],
              ["loading_service", t("shipment.loadingService")],
              ["unloading_service", t("shipment.unloadingService")],
            ].map(([k, lbl]) => (
              <label
                key={k}
                className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 cursor-pointer hover:border-slate-300"
              >
                <input
                  type="checkbox"
                  data-testid={`chk-${k}`}
                  checked={form[k]}
                  onChange={(e) => set(k, e.target.checked)}
                  className="w-4 h-4 accent-[#F1701E]"
                />
                <span className="text-sm text-slate-700">{lbl}</span>
              </label>
            ))}
          </div>
        </Card>

        {/* Pricing — advisory price + customer target price. Placed AFTER services
            so it reflects all price-affecting inputs. Maps are untouched. */}
        <Card data-testid="section-pricing">
          <div className="flex items-center gap-2 mb-3">
            <Wallet className="w-5 h-5 text-[#F1701E]" />
            <h2 className="font-bold text-base text-[#16233A]">{t("shipment.advisoryPrice")}</h2>
          </div>
          {!pricing ? (
            <p className="text-sm text-slate-400" data-testid="pricing-hint">{t("shipment.pricingSelectFirst")}</p>
          ) : (
            <div className="space-y-4">
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-slate-500">{t("shipment.advisoryPrice")}</span>
                <span className="text-2xl font-extrabold text-[#16233A]" data-testid="advisory-price">
                  {pricing.advisory_price} <span className="text-sm font-semibold">{pricing.pricing_currency}</span>
                </span>
              </div>
              <p className="text-xs text-slate-400">{t("shipment.advisoryHint")}</p>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-700">{t("shipment.targetPrice")}</span>
                  <span className="text-lg font-bold text-[#F1701E]" data-testid="max-offer-value">
                    {maxOffer} <span className="text-xs font-semibold">{pricing.pricing_currency}</span>
                  </span>
                </div>
                <input
                  type="range"
                  data-testid="max-offer-slider"
                  min={pricing.pricing_min}
                  max={pricing.pricing_max}
                  step={1}
                  value={maxOffer ?? pricing.advisory_price}
                  onChange={(e) => setMaxOffer(Number(e.target.value))}
                  className="w-full accent-[#F1701E]"
                />
                <div className="flex justify-between text-[11px] text-slate-400 mt-1 force-ltr">
                  <span>{pricing.pricing_min}</span>
                  <span>{pricing.pricing_max}</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">{t("shipment.targetHint")}</p>
              </div>
            </div>
          )}
        </Card>

        {/* 6. Summary + Publish button at bottom */}
        <Card data-testid="section-summary" className="bg-slate-50 border-slate-200">
          <h2 className="font-bold text-base text-[#16233A] mb-3">{t("shipment.summary")}</h2>
          <div className="space-y-2 text-sm">
            <div className="flex gap-2">
              <span className="text-slate-400 shrink-0">{t("shipment.description")}:</span>
              <span
                className="font-semibold text-slate-700 break-words"
                data-testid="summary-title"
              >
                {form.title.trim() || "—"}
              </span>
            </div>
            <div data-testid="summary-route">
              <RouteDisplay
                pickup={form.pickup_location}
                delivery={form.delivery_location}
              />
            </div>
            {(form.pickup_date || form.delivery_date) && (
              <div className="flex gap-2" data-testid="summary-dates">
                <span className="text-slate-400 shrink-0">{t("shipment.schedule")}:</span>
                <span className="font-semibold text-slate-700">
                  {form.pickup_date || "—"} {form.pickup_time && `(${form.pickup_time})`} →{" "}
                  {form.delivery_date || "—"} {form.delivery_time && `(${form.delivery_time})`}
                </span>
              </div>
            )}
            <div className="flex gap-2" data-testid="summary-services">
              <span className="text-slate-400 shrink-0">
                {t("shipment.selectedServices")}:
              </span>
              <span className="font-semibold text-slate-700">
                {selectedServices.length > 0
                  ? selectedServices.join(" · ")
                  : t("shipment.noServices")}
              </span>
            </div>
          </div>
          <div className="mt-4">
            <Btn
              variant="accent"
              onClick={submit}
              disabled={saving}
              data-testid="publish-btn"
              className="w-full justify-center"
            >
              <Check className="w-4 h-4" /> {t("common.publish")}
            </Btn>
          </div>
        </Card>
      </div>
    </div>
  );
}
