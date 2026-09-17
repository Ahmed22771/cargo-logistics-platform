import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, Check, Package, MapPin, Calendar, Truck, ClipboardCheck, Image as ImageIcon, X, Boxes } from "lucide-react";
import { Card, Btn, Field, Input, Textarea } from "../../components/ui-kit";
import { MapPicker } from "../../components/MapPicker";
import { RouteDisplay } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const VEHICLE_TYPES = ["pickup", "flatbed", "container", "refrigerated", "trailer"];

export default function CreateShipment() {
  const { t, isRTL, lang } = useI18n();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    title: "", category: "", category_key: "", description: "", quantity: "", weight: "", weight_unit: "kg",
    packages: "", dimensions: "", fragile: false, images: [],
    special_instructions: "", expected_price: "",
    pickup_location: null, delivery_location: null,
    pickup_date: "", pickup_time: "", delivery_date: "", delivery_time: "",
    vehicle_type: "flatbed", required_capacity: "", loading_service: false, unloading_service: false,
  });
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => { api.get("/categories").then(({ data }) => setCategories(data)).catch(() => setCategories([])); }, []);

  const steps = [
    { key: "cat", label: t("p11.wiz.whatShipment"), icon: Package },
    { key: "details", label: t("shipment.cargoDetails"), icon: Boxes },
    { key: "photos", label: t("p11.wiz.photos"), icon: ImageIcon },
    { key: "from", label: t("common.from"), icon: MapPin },
    { key: "to", label: t("common.to"), icon: MapPin },
    { key: "schedule", label: t("shipment.stepSchedule"), icon: Calendar },
    { key: "vehicle", label: t("shipment.stepVehicle"), icon: Truck },
    { key: "review", label: t("shipment.stepReview"), icon: ClipboardCheck },
  ];

  const canNext = () => {
    if (step === 0) return !!form.category_key;
    if (step === 3) return !!form.pickup_location;
    if (step === 4) return !!form.delivery_location;
    return true;
  };
  const next = () => {
    if (step === 0 && !form.category_key) { toast.error(t("p11.wiz.selectCategory")); return; }
    if (step === 3 && !form.pickup_location) { toast.error(t("shipment.missingPickup")); return; }
    if (step === 4 && !form.delivery_location) { toast.error(t("shipment.missingDelivery")); return; }
    setStep((s) => Math.min(s + 1, steps.length - 1));
  };

  const pickCategory = (c) => {
    set("category_key", c.key);
    set("category", lang === "ar" ? c.name_ar : c.name_en);
    if (!form.title) set("title", lang === "ar" ? c.name_ar : c.name_en);
  };

  const handleFiles = async (e) => {
    const files = Array.from(e.target.files || []).slice(0, 6);
    const readers = await Promise.all(files.map((f) => new Promise((res) => {
      const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(f);
    })));
    set("images", [...form.images, ...readers].slice(0, 6));
  };
  const removeImg = (i) => set("images", form.images.filter((_, idx) => idx !== i));

  const submit = async (status) => {
    if (status === "PUBLISHED") {
      if (!form.pickup_location && !form.delivery_location) { toast.error(t("shipment.missingBoth")); setStep(3); return; }
      if (!form.pickup_location) { toast.error(t("shipment.missingPickup")); setStep(3); return; }
      if (!form.delivery_location) { toast.error(t("shipment.missingDelivery")); setStep(4); return; }
    }
    if (!form.title) set("title", form.category || "Shipment");
    setSaving(true);
    try {
      await api.post("/shipments", { ...form, title: form.title || form.category || "Shipment", status });
      toast.success(status === "PUBLISHED" ? t("shipment.publishedSuccess") : t("shipment.createdSuccess"));
      navigate("/customer/shipments");
    } catch (err) {
      const code = apiErr(err);
      const map = { MISSING_PICKUP: t("shipment.missingPickup"), MISSING_DELIVERY: t("shipment.missingDelivery"), MISSING_BOTH: t("shipment.missingBoth") };
      toast.error(map[code] || code);
    } finally { setSaving(false); }
  };

  const vLabel = (v) => t(`shipment.vehicle${v.charAt(0).toUpperCase() + v.slice(1)}`);

  return (
    <div className="max-w-2xl mx-auto">
      <button onClick={() => navigate("/customer/shipments")} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4" data-testid="wizard-back-list">
        <ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} /> {t("nav.myShipments")}
      </button>
      <h1 className="text-2xl font-extrabold text-[#16233A] mb-1">{t("shipment.create")}</h1>

      <div className="flex items-center gap-1 my-5 overflow-x-auto pb-2">
        {steps.map((s, i) => (
          <React.Fragment key={s.key}>
            <div className={`flex items-center gap-2 shrink-0 ${i === step ? "" : "opacity-60"}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${i < step ? "bg-emerald-500 text-white" : i === step ? "bg-[#F1701E] text-white" : "bg-slate-200 text-slate-500"}`}>
                {i < step ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              <span className={`text-xs font-semibold hidden sm:block whitespace-nowrap ${i === step ? "text-[#16233A]" : "text-slate-400"}`}>{s.label}</span>
            </div>
            {i < steps.length - 1 && <div className="w-4 h-px bg-slate-200 shrink-0" />}
          </React.Fragment>
        ))}
      </div>

      <Card className="animate-fade-in">
        {step === 0 && (
          <div data-testid="step-category">
            <h2 className="font-bold text-lg text-[#16233A] mb-1">{t("p11.wiz.whatShipment")}</h2>
            <p className="text-sm text-slate-400 mb-4">{t("p11.wiz.selectCategory")}</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {categories.map((c) => (
                <button key={c.key} type="button" data-testid={`cat-${c.key}`} onClick={() => pickCategory(c)}
                  className={`p-4 rounded-xl border text-sm font-semibold transition-all ${form.category_key === c.key ? "border-[#F1701E] bg-orange-50 text-[#16233A]" : "border-slate-200 text-slate-600 hover:border-slate-300"}`}>
                  <Package className="w-5 h-5 mx-auto mb-2 text-[#F1701E]" /> {lang === "ar" ? c.name_ar : c.name_en}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4" data-testid="step-details">
            <h2 className="font-bold text-lg text-[#16233A]">{t("shipment.cargoDetails")}</h2>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("shipment.quantity")}><Input data-testid="ship-qty" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} className="force-ltr" /></Field>
              <Field label={t("p11.wiz.packages")}><Input data-testid="ship-packages" value={form.packages} onChange={(e) => set("packages", e.target.value)} className="force-ltr" /></Field>
              <Field label={t("shipment.weight")}><Input data-testid="ship-weight" value={form.weight} onChange={(e) => set("weight", e.target.value)} className="force-ltr" /></Field>
              <Field label={t("p11.wiz.weightUnit")}>
                <select data-testid="ship-weight-unit" value={form.weight_unit} onChange={(e) => set("weight_unit", e.target.value)} className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#F1701E]">
                  <option value="kg">kg</option><option value="ton">ton</option>
                </select>
              </Field>
              <Field label={t("shipment.dimensions")}><Input data-testid="ship-dims" value={form.dimensions} onChange={(e) => set("dimensions", e.target.value)} /></Field>
            </div>
            <Field label={t("shipment.description")}><Textarea data-testid="ship-desc" rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} /></Field>
            <Field label={t("shipment.specialInstructions")}><Textarea data-testid="ship-instructions" rows={2} value={form.special_instructions} onChange={(e) => set("special_instructions", e.target.value)} /></Field>
            <div className="flex flex-col gap-2">
              {[["fragile", t("p11.wiz.fragile")], ["loading_service", t("shipment.loadingService")], ["unloading_service", t("shipment.unloadingService")]].map(([k, lbl]) => (
                <label key={k} className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 cursor-pointer">
                  <input type="checkbox" data-testid={`chk-${k}`} checked={form[k]} onChange={(e) => set(k, e.target.checked)} className="w-4 h-4 accent-[#F1701E]" />
                  <span className="text-sm text-slate-700">{lbl}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4" data-testid="step-photos">
            <div><h2 className="font-bold text-lg text-[#16233A]">{t("p11.wiz.photos")}</h2><p className="text-sm text-slate-400">{t("p11.wiz.photosOptional")}</p></div>
            <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl p-8 cursor-pointer hover:border-[#F1701E] transition-colors" data-testid="photo-upload-label">
              <ImageIcon className="w-8 h-8 text-slate-400" />
              <span className="text-sm font-semibold text-[#16233A]">{t("p11.wiz.addPhotos")}</span>
              <input type="file" accept="image/*" multiple className="hidden" data-testid="photo-input" onChange={handleFiles} />
            </label>
            {form.images.length > 0 && (
              <div className="grid grid-cols-3 gap-3">
                {form.images.map((src, i) => (
                  <div key={i} className="relative group aspect-square rounded-lg overflow-hidden border border-slate-200">
                    <img src={src} alt="" className="w-full h-full object-cover" />
                    <button type="button" data-testid={`remove-img-${i}`} onClick={() => removeImg(i)} className="absolute top-1 end-1 bg-black/60 text-white rounded-full p-1"><X className="w-3.5 h-3.5" /></button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3" data-testid="step-from">
            <div><h2 className="font-bold text-lg text-[#F1701E]">{t("p11.wiz.whereShipment")}</h2><p className="text-xs text-slate-400 mt-0.5">{t("common.from")} / من — {t("p11.wiz.originHint")}</p></div>
            <MapPicker testIdPrefix="pickup-map" value={form.pickup_location} confirmLabel={t("shipment.confirmPickup")}
              onConfirm={(loc) => { set("pickup_location", loc); toast.success(t("shipment.confirmPickup")); }} />
            {form.pickup_location && <div className="text-sm text-emerald-600 font-semibold flex items-center gap-1.5"><Check className="w-4 h-4" /> {form.pickup_location.address || t("p11.map.unnamed")}</div>}
          </div>
        )}

        {step === 4 && (
          <div className="space-y-3" data-testid="step-to">
            <div><h2 className="font-bold text-lg text-[#16233A]">{t("p11.wiz.whereDeliver")}</h2><p className="text-xs text-slate-400 mt-0.5">{t("common.to")} / إلى — {t("p11.wiz.destHint")}</p></div>
            <MapPicker testIdPrefix="delivery-map" value={form.delivery_location} accentConfirm={false} confirmLabel={t("shipment.confirmDelivery")}
              onConfirm={(loc) => { set("delivery_location", loc); toast.success(t("shipment.confirmDelivery")); }} />
            {form.delivery_location && <div className="text-sm text-emerald-600 font-semibold flex items-center gap-1.5"><Check className="w-4 h-4" /> {form.delivery_location.address || t("p11.map.unnamed")}</div>}
          </div>
        )}

        {step === 5 && (
          <div className="space-y-4" data-testid="step-schedule">
            <h2 className="font-bold text-lg text-[#16233A]">{t("shipment.schedule")}</h2>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("shipment.pickupDate")}><Input type="date" data-testid="ship-pickup-date" value={form.pickup_date} onChange={(e) => set("pickup_date", e.target.value)} className="force-ltr" /></Field>
              <Field label={t("common.time")}><Input type="time" value={form.pickup_time} onChange={(e) => set("pickup_time", e.target.value)} className="force-ltr" /></Field>
              <Field label={t("shipment.deliveryDate")}><Input type="date" data-testid="ship-delivery-date" value={form.delivery_date} onChange={(e) => set("delivery_date", e.target.value)} className="force-ltr" /></Field>
              <Field label={t("common.time")}><Input type="time" value={form.delivery_time} onChange={(e) => set("delivery_time", e.target.value)} className="force-ltr" /></Field>
            </div>
          </div>
        )}

        {step === 6 && (
          <div className="space-y-4" data-testid="step-vehicle">
            <h2 className="font-bold text-lg text-[#16233A]">{t("shipment.vehicleType")}</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {VEHICLE_TYPES.map((v) => (
                <button key={v} type="button" data-testid={`vehicle-${v}`} onClick={() => set("vehicle_type", v)}
                  className={`p-4 rounded-xl border text-sm font-semibold transition-all ${form.vehicle_type === v ? "border-[#F1701E] bg-orange-50 text-[#16233A]" : "border-slate-200 text-slate-500 hover:border-slate-300"}`}>
                  <Truck className="w-5 h-5 mx-auto mb-2" /> {vLabel(v)}
                </button>
              ))}
            </div>
            <Field label={t("shipment.requiredCapacity")}><Input data-testid="ship-capacity" value={form.required_capacity} onChange={(e) => set("required_capacity", e.target.value)} className="force-ltr" /></Field>
            <Field label={t("shipment.expectedPrice")} hint={t("common.currency")}><Input data-testid="ship-price" value={form.expected_price} onChange={(e) => set("expected_price", e.target.value)} className="force-ltr" /></Field>
          </div>
        )}

        {step === 7 && (
          <div className="space-y-4" data-testid="step-review">
            <h2 className="font-bold text-lg text-[#16233A]">{t("shipment.review")}</h2>
            <p className="text-sm text-slate-400">{t("shipment.reviewNote")}</p>
            <div className="bg-slate-50 rounded-xl p-4">
              <div className="font-bold text-[#16233A]">{form.category} {form.title && form.title !== form.category ? `· ${form.title}` : ""}</div>
              {form.description && <p className="text-sm text-slate-500 mt-1">{form.description}</p>}
              {form.images.length > 0 && <div className="flex gap-2 mt-3">{form.images.slice(0, 4).map((s, i) => <img key={i} src={s} alt="" className="w-14 h-14 rounded-lg object-cover border" />)}</div>}
              <div className="mt-3"><RouteDisplay pickup={form.pickup_location} delivery={form.delivery_location} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[[t("shipment.quantity"), form.quantity], [t("shipment.weight"), form.weight ? `${form.weight} ${form.weight_unit}` : ""],
                [t("p11.wiz.packages"), form.packages], [t("shipment.vehicleType"), vLabel(form.vehicle_type)],
                [t("shipment.pickupDate"), form.pickup_date], [t("shipment.expectedPrice"), form.expected_price ? `${form.expected_price} ${t("common.currency")}` : "—"]].map(([l, v], i) => (
                <div key={i} className="border border-slate-100 rounded-lg p-2.5"><div className="text-xs text-slate-400">{l}</div><div className="font-semibold text-slate-700">{v || "—"}</div></div>
              ))}
            </div>
          </div>
        )}
      </Card>

      <div className="flex items-center justify-between gap-3 mt-5">
        <div className="flex gap-2">
          {step > 0 && <Btn variant="secondary" onClick={() => setStep((s) => s - 1)} data-testid="wizard-back-btn"><ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} /> {t("common.back")}</Btn>}
          <Btn variant="ghost" onClick={() => submit("DRAFT")} disabled={saving || !form.category_key} data-testid="save-draft-btn">{t("common.saveDraft")}</Btn>
        </div>
        {step < steps.length - 1 ? (
          <Btn variant="primary" onClick={next} disabled={!canNext()} data-testid="wizard-next-btn">{t("common.next")} <ArrowRight className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} /></Btn>
        ) : (
          <Btn variant="accent" onClick={() => submit("PUBLISHED")} disabled={saving} data-testid="publish-btn"><Check className="w-4 h-4" /> {t("common.publish")}</Btn>
        )}
      </div>
    </div>
  );
}
