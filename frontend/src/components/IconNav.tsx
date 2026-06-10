import { NavLink } from "react-router-dom";
import { Inbox as InboxIcon, PenSquare, MessageCircle, BarChart3, BookOpen, Shield } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Role } from "../lib/types";

interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
  roles?: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/inbox", icon: InboxIcon, label: "Bejövő" },
  { to: "/new", icon: PenSquare, label: "Új ügy" },
  { to: "/copilot", icon: MessageCircle, label: "Copilot" },
  { to: "/eval", icon: BarChart3, label: "Értékelés" },
  { to: "/knowledge", icon: BookOpen, label: "Tudástár" },
  { to: "/supervisor", icon: Shield, label: "Superv.", roles: ["supervisor"] },
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
              <item.icon
                size={18}
                className={isActive ? "text-one-turq-d" : "text-one-grey"}
                aria-hidden="true"
              />
              <span>{item.label}</span>
              {isActive && <span className="sr-only">(aktív)</span>}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
