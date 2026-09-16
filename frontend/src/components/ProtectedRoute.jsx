import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { CargoLogo } from "./CargoLogo";

export function LoadingScreen() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-slate-50" data-testid="loading-screen">
      <CargoLogo size={48} />
      <div className="w-8 h-8 border-3 border-slate-200 border-t-[#F1701E] rounded-full animate-spin" />
    </div>
  );
}

export function ProtectedRoute({ roles, redirect = "/login", children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to={redirect} replace />;
  if (roles && !roles.includes(user.role)) {
    const home = user.role === "admin" ? "/admin" : `/${user.role}`;
    return <Navigate to={home} replace />;
  }
  return children;
}
