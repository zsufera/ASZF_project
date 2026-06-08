import { NavLink } from "react-router-dom";
import type { Role } from "../lib/types";

interface NavItem {
  to: string;
  icon: string;
  label: string;
  roles?: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/inbox", icon: "📥", label: "Inbox" },
  { to: "/new", icon: "✏️", label: "Új ügy" },
  { to: "/copilot", icon: "💬", label: "Copilot" },
  { to: "/postal", icon: "📮", label: "Postai levél" },
  { to: "/eval", icon: "📊", label: "Evaluation" },
  { to: "/supervisor", icon: "🛡️", label: "Superv.", roles: ["supervisor"] },
];

export function IconNav({ role }: { role: Role }) {
  const items = NAV_ITEMS.filter((i) => !i.roles || i.roles.includes(role));
  return (
    <nav
      aria-label="Főnavigáció"
      className="w-[70px] bg-one-surface border-r border-one-line flex flex-col gap-1.5 py-3 items-center"
      style={{ minHeight: "calc(100vh - var(--header-h))" }}
    >
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          aria-current={undefined}
          className={({ isActive }) =>
            `w-[50px] h-[44px] rounded-xl flex flex-col items-center justify-center gap-0.5 text-[9px] transition-colors duration-100 ${
              isActive
                ? "bg-one-turq-l text-one-turq-d font-semibold"
                : "text-one-grey hover:bg-one-canvas"
            }`
          }
          aria-label={item.label}
        >
          {({ isActive }) => (
            <>
              <span className="text-[17px]" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
              {isActive && <span className="sr-only">(aktív)</span>}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
