import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Employees = lazy(() => import("@/pages/Employees"));
const EmployeeDetail = lazy(() => import("@/pages/EmployeeDetail"));
const Insights = lazy(() => import("@/pages/Insights"));
const SalarySlips = lazy(() => import("@/pages/SalarySlips"));
const TaxRules = lazy(() => import("@/pages/admin/TaxRules"));
const PFRules = lazy(() => import("@/pages/admin/PFRules"));
const Users = lazy(() => import("@/pages/admin/Users"));
const Calculator = lazy(() => import("@/pages/Calculator"));

export default function Router() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading…</div>}>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/employees" element={<Employees />} />
                    <Route path="/employees/:id" element={<EmployeeDetail />} />
                    <Route path="/insights" element={<Insights />} />
                    <Route path="/calculator" element={<Calculator />} />
                    <Route path="/my/salary-slips" element={<SalarySlips />} />
                    <Route path="/admin/tax-rules" element={<TaxRules />} />
                    <Route path="/admin/pf-rules" element={<PFRules />} />
                    <Route path="/admin/users" element={<Users />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Suspense>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
