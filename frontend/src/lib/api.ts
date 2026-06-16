import axios from "axios";
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "./auth";

const api = axios.create({ baseURL: "/" });

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = getRefreshToken();
      if (refresh) {
        try {
          const { data } = await axios.post("/auth/refresh", { refresh_token: refresh });
          setTokens(data.access_token, refresh);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          clearTokens();
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password }).then((r) => r.data);
export const getMe = () => api.get("/auth/me").then((r) => r.data);

// Employees
export const listEmployees = (params: Record<string, unknown>) =>
  api.get("/api/employees", { params }).then((r) => r.data);
export const getEmployee = (id: number) =>
  api.get(`/api/employees/${id}`).then((r) => r.data);
export const createEmployee = (data: unknown) =>
  api.post("/api/employees", data).then((r) => r.data);
export const updateEmployee = (id: number, data: unknown) =>
  api.put(`/api/employees/${id}`, data).then((r) => r.data);

// Compensation
export const listSalaryRecords = (employeeId: number) =>
  api.get(`/api/employees/${employeeId}/salary-records`).then((r) => r.data);
export const createSalaryRecord = (employeeId: number, data: unknown) =>
  api.post(`/api/employees/${employeeId}/salary-records`, data).then((r) => r.data);
export const listBonuses = (employeeId: number) =>
  api.get(`/api/employees/${employeeId}/bonuses`).then((r) => r.data);
export const listAllowances = (employeeId: number) =>
  api.get(`/api/employees/${employeeId}/allowances`).then((r) => r.data);
export const listDeductions = (employeeId: number) =>
  api.get(`/api/employees/${employeeId}/deductions`).then((r) => r.data);

// Salary slips
export const generateSalarySlip = (employeeId: number, month: number, year: number) =>
  api.post(`/api/employees/${employeeId}/salary-slips/generate`, { period_month: month, period_year: year }).then((r) => r.data);
export const listSalarySlips = (employeeId: number) =>
  api.get(`/api/employees/${employeeId}/salary-slips`).then((r) => r.data);

// Analytics
export const getAnalyticsSummary = (params?: Record<string, unknown>) =>
  api.get("/api/analytics/summary", { params }).then((r) => r.data);
export const getAnalyticsByDepartment = () =>
  api.get("/api/analytics/by-department").then((r) => r.data);
export const getAnalyticsByCountry = () =>
  api.get("/api/analytics/by-country").then((r) => r.data);
export const getSalaryBands = (bucketSize = 5000) =>
  api.get("/api/analytics/salary-bands", { params: { bucket_size: bucketSize } }).then((r) => r.data);

// AI
export const aiQuery = (question: string) =>
  api.post("/api/ai/query", { question }).then((r) => r.data);

// Meta
export const getDepartments = () => api.get("/api/meta/departments").then((r) => r.data);
export const getCountries = () => api.get("/api/meta/countries").then((r) => r.data);

// Tax rules
export const listTaxRules = () => api.get("/api/tax-rules").then((r) => r.data);
export const createTaxRule = (data: unknown) => api.post("/api/tax-rules", data).then((r) => r.data);

// PF rules
export const listPFRules = () => api.get("/api/pf-rules").then((r) => r.data);
export const createPFRule = (data: unknown) => api.post("/api/pf-rules", data).then((r) => r.data);

// Admin users
export const listUsers = () => api.get("/api/admin/users").then((r) => r.data);
export const createUser = (data: unknown) => api.post("/api/admin/users", data).then((r) => r.data);
export const updateUser = (id: number, data: unknown) => api.put(`/api/admin/users/${id}`, data).then((r) => r.data);

export default api;
