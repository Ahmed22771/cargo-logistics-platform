import React, { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  LayoutDashboard,
  ShieldCheck,
  Package,
  Gavel,
  Truck,
  Users,
  ScrollText,
  Wallet,
  KeyRound,
  FileText,
  Scale,
  MessageCircle,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { LoadingScreen } from "../../components/ProtectedRoute";
import api from "../../lib/api";
import AdminLogin from "./AdminLogin";
import { AdminLayout } from "./AdminLayout";
import AdminDashboard from "./AdminDashboard";
import AdminDrivers from "./AdminDrivers";
import AdminShipments from "./AdminShipments";
import AdminBids from "./AdminBids";
import AdminTrips from "./AdminTrips";
import AdminUsers from "./AdminUsers";
import AdminAudit from "./AdminAudit";
import AdminFinance from "./AdminFinance";
import AdminAccess from "./AdminAccess";
import AdminDocuments from "./AdminDocuments";
import AdminDisputes from "./AdminDisputes";
import AdminDisputeDetail from "./AdminDisputeDetail";
import AdminContracts from "./AdminContracts";
import AdminContractDetail from "./AdminContractDetail";
import Messages from "../../components/Messages";

// perm: null = visible to any admin; otherwise requires that permission
const NAV = [
  {
    key: "dashboard",
    to: "",
    label: "admin.dashboard",
    icon: LayoutDashboard,
    perm: null,
  },
  {
    key: "drivers",
    to: "/drivers",
    label: "nav.drivers",
    icon: ShieldCheck,
    perm: null,
  },
  {
    key: "shipments",
    to: "/shipments",
    label: "nav.shipments",
    icon: Package,
    perm: null,
  },
  {
    key: "bids",
    to: "/bids",
    label: "nav.bids",
    icon: Gavel,
    perm: null,
  },
  {
    key: "trips",
    to: "/trips",
    label: "nav.trips",
    icon: Truck,
    perm: null,
  },
  {
    key: "contracts",
    to: "/contracts",
    label: "nav.contracts",
    icon: FileText,
    perm: null,
  },
  {
    key: "disputes",
    to: "/disputes",
    label: "nav.disputes",
    icon: Scale,
    perm: "disputes.view",
  },
  {
    key: "messages",
    to: "/messages",
    label: "chat.title",
    icon: MessageCircle,
    perm: null,
  },
  {
    key: "documents",
    to: "/documents",
    label: "p4.docs.navTitle",
    icon: FileText,
    perm: "documents.view",
  },
  {
    key: "users",
    to: "/users",
    label: "nav.users",
    icon: Users,
    perm: "users.view",
  },
  {
    key: "finance",
    to: "/finance",
    label: "nav.finance",
    icon: Wallet,
    perm: "finance.view",
  },
  {
    key: "access",
    to: "/access",
    label: "nav.access",
    icon: KeyRound,
    perm: "system.roles",
  },
  {
    key: "audit",
    to: "/audit",
    label: "nav.auditLog",
    icon: ScrollText,
    perm: "system.audit",
  },
];

export default function AdminPortal() {
  const { user, loading } = useAuth();
  const [perms, setPerms] = useState(null);

  useEffect(() => {
    if (user && user.role === "admin") {
      api
        .get("/admin/me/permissions")
        .then(({ data }) => setPerms(data.permissions || []))
        .catch(() => setPerms([]));
    }
  }, [user]);

  if (loading) return <LoadingScreen />;

  // Separate admin auth experience: only ADMIN role can enter,
  // everyone else sees admin login.
  if (!user || user.role !== "admin") return <AdminLogin />;

  const nav = NAV.filter(
    (n) => !n.perm || (perms || []).includes(n.perm)
  );

  return (
    <AdminLayout navItems={nav}>
      <Routes>
        <Route index element={<AdminDashboard />} />
        <Route path="drivers" element={<AdminDrivers />} />
        <Route path="shipments" element={<AdminShipments />} />
        <Route path="bids" element={<AdminBids />} />
        <Route path="trips" element={<AdminTrips />} />
        <Route path="contracts" element={<AdminContracts />} />
        <Route path="contracts/:contractId"element={<AdminContractDetail />}/>
        <Route path="disputes" element={<AdminDisputes />} />
        <Route
          path="disputes/:tripId"
          element={<AdminDisputeDetail />}
        />
        <Route
          path="messages"
          element={<Messages basePath="/admin" />}
        />
        <Route
          path="messages/:cid"
          element={<Messages basePath="/admin" />}
        />
        <Route path="documents" element={<AdminDocuments />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="finance" element={<AdminFinance />} />
        <Route path="access" element={<AdminAccess />} />
        <Route path="audit" element={<AdminAudit />} />
        <Route
          path="*"
          element={<Navigate to="/admin" replace />}
        />
      </Routes>
    </AdminLayout>
  );
}