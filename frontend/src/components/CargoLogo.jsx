import React from "react";

// CARGO logo mark derived from brand: navy C-ring + orange motion bars
export function LogoMark({ size = 36 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <path
        d="M78 26 A34 34 0 1 0 78 74"
        stroke="#16233A" strokeWidth="15" strokeLinecap="round" fill="none"
      />
      <rect x="26" y="40" width="34" height="6.5" rx="3.25" fill="#F1701E" />
      <rect x="20" y="50" width="40" height="6.5" rx="3.25" fill="#F1701E" />
      <rect x="30" y="60" width="30" height="6.5" rx="3.25" fill="#F1701E" />
    </svg>
  );
}

export function CargoLogo({ size = 36, showText = true, dark = false, className = "" }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`} data-testid="cargo-logo">
      <LogoMark size={size} />
      {showText && (
        <div className="flex flex-col leading-none">
          <span
            className="font-extrabold tracking-tight"
            style={{ color: dark ? "#fff" : "#16233A", fontSize: size * 0.55, fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            CARGO
          </span>
          <span className="font-semibold" style={{ color: "#F1701E", fontSize: size * 0.3, fontFamily: "'Cairo', sans-serif" }}>
            كارجو
          </span>
        </div>
      )}
    </div>
  );
}
