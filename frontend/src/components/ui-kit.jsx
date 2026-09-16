import React from "react";
import { Loader2 } from "lucide-react";

export function Card({ children, className = "", ...props }) {
  return (
    <div className={`bg-white border border-slate-200 rounded-xl shadow-sm p-5 md:p-6 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function Btn({ variant = "primary", className = "", children, ...props }) {
  const variants = {
    primary: "bg-[#16233A] hover:bg-[#0E1726] text-white",
    accent: "bg-[#F1701E] hover:bg-[#D95E0E] text-white",
    secondary: "bg-slate-100 hover:bg-slate-200 text-[#16233A]",
    outline: "border border-[#16233A] text-[#16233A] hover:bg-[#16233A]/5",
    ghost: "text-slate-600 hover:bg-slate-100",
    danger: "bg-red-600 hover:bg-red-700 text-white",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 font-semibold py-2.5 px-5 rounded-lg transition-all duration-150 active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none text-sm ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Field({ label, required, children, hint, error }) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-sm font-semibold text-slate-700">
          {label} {required && <span className="text-[#F1701E]">*</span>}
        </label>
      )}
      {children}
      {hint && !error && <p className="text-xs text-slate-400">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function Input(props) {
  return (
    <input
      {...props}
      className={`w-full bg-white border border-slate-300 focus:border-[#F1701E] focus:ring-2 focus:ring-[#F1701E]/20 rounded-lg px-3.5 py-2.5 text-slate-900 placeholder:text-slate-400 text-sm outline-none transition-all ${props.className || ""}`}
    />
  );
}

export function Textarea(props) {
  return (
    <textarea
      {...props}
      className={`w-full bg-white border border-slate-300 focus:border-[#F1701E] focus:ring-2 focus:ring-[#F1701E]/20 rounded-lg px-3.5 py-2.5 text-slate-900 placeholder:text-slate-400 text-sm outline-none transition-all ${props.className || ""}`}
    />
  );
}

export function Spinner({ label }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-400" data-testid="spinner">
      <Loader2 className="w-7 h-7 animate-spin text-[#F1701E]" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, subtitle, action, testId }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center px-6" data-testid={testId || "empty-state"}>
      {Icon && <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mb-4"><Icon className="w-7 h-7 text-slate-400" /></div>}
      <h3 className="text-base font-semibold text-slate-700">{title}</h3>
      {subtitle && <p className="text-sm text-slate-400 mt-1 max-w-sm">{subtitle}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-[#16233A]">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
