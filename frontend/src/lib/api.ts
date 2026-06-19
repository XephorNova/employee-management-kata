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

// AI usage
export interface AIUsage {
  tokens_used: number;
  tokens_limit: number;
  tokens_remaining: number;
  resets_at: string;
}

export const getAIUsage = (): Promise<AIUsage> =>
  api.get("/api/ai/usage").then((r) => r.data);

// Meta
export const getDepartments = () => api.get("/api/meta/departments").then((r) => r.data);
export const getCountries = () => api.get("/api/meta/countries").then((r) => r.data);

// Tax rules
export const listTaxRules = () => api.get("/api/tax-rules").then((r) => r.data);
export const createTaxRule = (data: unknown) => api.post("/api/tax-rules", data).then((r) => r.data);
export const addTaxBracket = (ruleId: number, data: unknown) => api.post(`/api/tax-rules/${ruleId}/brackets`, data).then((r) => r.data);
export const deleteTaxBracket = (ruleId: number, bracketId: number) => api.delete(`/api/tax-rules/${ruleId}/brackets/${bracketId}`);

// PF rules
export const listPFRules = () => api.get("/api/pf-rules").then((r) => r.data);
export const createPFRule = (data: unknown) => api.post("/api/pf-rules", data).then((r) => r.data);
export const updatePFRule = (id: number, data: unknown) => api.put(`/api/pf-rules/${id}`, data).then((r) => r.data);

// Bank details
export const listBankDetails = (employeeId: number) => api.get(`/api/employees/${employeeId}/bank-details`).then((r) => r.data);
export const createBankDetail = (employeeId: number, data: unknown) => api.post(`/api/employees/${employeeId}/bank-details`, data).then((r) => r.data);
export const updateBankDetail = (employeeId: number, detailId: number, data: unknown) => api.put(`/api/employees/${employeeId}/bank-details/${detailId}`, data).then((r) => r.data);
export const deleteBankDetail = (employeeId: number, detailId: number) => api.delete(`/api/employees/${employeeId}/bank-details/${detailId}`);

// Bulk salary generation
export const bulkGenerateSalarySlips = (month: number, year: number) =>
  api.post("/api/salary-slips/bulk-generate", { period_month: month, period_year: year }).then((r) => r.data);

// Tax statement
export const getTaxStatement = (employeeId: number, year: number) =>
  api.get(`/api/employees/${employeeId}/tax-statement/${year}`).then((r) => r.data);

export async function downloadSlipPdf(
  employeeId: number,
  year: number,
  month: number,
): Promise<void> {
  const response = await api.get(
    `/api/employees/${employeeId}/salary-slips/${year}/${month}/pdf`,
    { responseType: "blob" },
  );
  const url = URL.createObjectURL(
    new Blob([response.data], { type: "application/pdf" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = `slip_${employeeId}_${year}_${String(month).padStart(2, "0")}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Delay revocation so the browser has time to start reading the blob URL.
  setTimeout(() => URL.revokeObjectURL(url), 100);
}

// Admin users
export const listUsers = () => api.get("/api/admin/users").then((r) => r.data);
export const createUser = (data: unknown) => api.post("/api/admin/users", data).then((r) => r.data);
export const updateUser = (id: number, data: unknown) => api.put(`/api/admin/users/${id}`, data).then((r) => r.data);

// Calculator
export interface CalculatorRequest {
  country: string;
  base_salary: number;
  pay_frequency: "monthly" | "annual";
  allowances: number;
  other_deductions: number;
  currency: string;
}

export interface CalculatorResponse {
  gross_salary: number;
  pf_employee_contribution: number;
  pf_employer_contribution: number;
  tax_deducted: number;
  taxable_income: number;
  other_deductions: number;
  net_take_home: number;
  currency: string;
  tax_rule_applied: string | null;
  pf_rule_applied: string | null;
  no_rules_warning: boolean;
}

export const calculateNetSalary = (data: CalculatorRequest): Promise<CalculatorResponse> =>
  api.post("/api/calculator/calculate", data).then((r) => r.data);

export default api;
