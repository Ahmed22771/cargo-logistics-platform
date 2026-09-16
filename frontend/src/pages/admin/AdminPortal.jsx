import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { LayoutDashboard, ShieldCheck, Package, Gavel, Truck, Users, ScrollText } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { LoadingScreen } from "../../components/ProtectedRoute";
import AdminLogin from "./AdminLogin";
import { AdminLayout } from "./AdminLayout";
import AdminDashboard from "./AdminDashboard";
import AdminDrivers from "./AdminDrivers";
import AdminShipments from "./AdminShipments";
import AdminBids from "./AdminBids";
import AdminTrips from "./AdminTrips";
import AdminUsers from "./AdminUsers";
import AdminAudit from "./AdminAudit";

const NAV = [
  { key: "dashboard", to: "", label: "admin.dashboard", icon: LayoutDashboard },
  { key: "drivers", to: "/drivers", label: "nav.drivers", icon: ShieldCheck },
  { key: "shipments", to: "/shipments", label: "nav.shipments", icon: Package },
  { key: "bids", to: "/bids", label: "nav.bids", icon: Gavel },
  { key: "trips", to: "/trips", label: "nav.trips", icon: Truck },
  { key: "users", to: "/users", label: "nav.users", icon: Users },
  { key: "audit", to: "/audit", label: "nav.auditLog", icon: ScrollText },
];

export default function AdminPortal() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  // Separate admin auth experience: only ADMIN role can enter, everyone else sees admin login
  if (!user || user.role !== "admin") return <AdminLogin />;
  return (
    <AdminLayout navItems={NAV}>
      <Routes>
        <Route index element={<AdminDashboard />} />
        <Route path="drivers" element={<AdminDrivers />} />
        <Route path="shipments" element={<AdminShipments />} />
        <Route path="bids" element={<AdminBids />} />
        <Route path="trips" element={<AdminTrips />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="audit" element={<AdminAudit />} />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </AdminLayout>
  );
}
