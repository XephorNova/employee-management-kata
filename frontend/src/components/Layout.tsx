import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  FileText,
  Briefcase,
  UserCog,
  Receipt,
  Layers,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/employees", label: "Employees", icon: Users, roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/insights", label: "AI Insights", icon: MessageSquare, roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/admin/tax-rules", label: "Tax Rules", icon: FileText, roles: ["admin", "hr_manager"], section: "Admin" },
  { href: "/admin/pf-rules", label: "PF Rules", icon: Briefcase, roles: ["admin", "hr_manager"] },
  { href: "/admin/users", label: "Users", icon: UserCog, roles: ["admin"] },
  { href: "/my/salary-slips", label: "My Slips", icon: Receipt, roles: ["employee"] },
];

const routeTitles: Record<string, string> = {
  "/": "Dashboard",
  "/employees": "Employees",
  "/insights": "AI Insights",
  "/admin/tax-rules": "Tax Rules",
  "/admin/pf-rules": "PF Rules",
  "/admin/users": "Users",
  "/my/salary-slips": "My Salary Slips",
};

function getPageTitle(pathname: string): string {
  if (routeTitles[pathname]) return routeTitles[pathname];
  if (pathname.startsWith("/employees/")) return "Employee Detail";
  return "ACME HR";
}

function initial(email: string): string {
  return email.charAt(0).toUpperCase();
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const visibleNav = navItems.filter(
    (item) => user && item.roles.includes(user.role)
  );

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const pageTitle = getPageTitle(location.pathname);

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-52 bg-slate-900 text-white flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="p-4 flex items-center gap-2.5 border-b border-slate-700/60">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <Layers className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-base tracking-tight">ACME HR</span>
        </div>

        {/* Nav */}
        <nav aria-label="Main navigation" className="flex-1 py-3">
          {visibleNav.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.href);
            return (
              <div key={item.href}>
                {item.section && (
                  <p className="px-4 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                    {item.section}
                  </p>
                )}
                <Link
                  to={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors border-l-2",
                    isActive
                      ? "bg-slate-800 text-white border-indigo-500"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white border-transparent"
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {item.label}
                </Link>
              </div>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="p-4 border-t border-slate-700/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-semibold flex-shrink-0">
              {user ? initial(user.email) : "?"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{user?.email}</p>
              <p className="text-xs text-slate-500 capitalize">
                {user?.role?.replace(/_/g, " ")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
          <h1 className="text-base font-semibold text-slate-900">{pageTitle}</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500 hidden sm:block">{user?.email}</span>
            <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-semibold text-white flex-shrink-0">
              {user ? initial(user.email) : "?"}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 bg-slate-100 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
