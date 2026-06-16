import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { getMe, login as apiLogin } from "@/lib/api";
import { setTokens, clearTokens } from "@/lib/auth";

interface User {
  id: number;
  email: string;
  role: "admin" | "hr_manager" | "hr_analyst" | "employee";
  employee_id: number | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const data = await apiLogin(email, password);
    setTokens(data.access_token, data.refresh_token);
    const me = await getMe();
    setUser(me);
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
