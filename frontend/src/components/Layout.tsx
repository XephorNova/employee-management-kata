import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/employees", label: "Employees", roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/insights", label: "AI Insights", roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/admin/tax-rules", label: "Tax Rules", roles: ["admin", "hr_manager"] },
  { href: "/admin/pf-rules", label: "PF Rules", roles: ["admin", "hr_manager"] },
  { href: "/admin/users", label: "Users", roles: ["admin"] },
  { href: "/my/salary-slips", label: "My Slips", roles: ["employee"] },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const visibleNav = navItems.filter((item) => user && item.roles.includes(user.role));

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-slate-900 text-white flex flex-col">
        <div className="p-4 font-bold text-lg border-b border-slate-700">ACME HR</div>
        <nav className="flex-1 py-4">
          {visibleNav.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "block px-4 py-2 text-sm hover:bg-slate-700 transition-colors",
                location.pathname === item.href && "bg-slate-700 font-medium"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-700 text-xs text-slate-400">
          <p>{user?.email}</p>
          <p className="capitalize">{user?.role?.replace("_", " ")}</p>
          <Button variant="ghost" size="sm" onClick={handleLogout} className="mt-2 text-slate-300 hover:text-white px-0">
            Sign out
          </Button>
        </div>
      </aside>
      <main className="flex-1 bg-slate-50 overflow-auto p-6">{children}</main>
    </div>
  );
}
