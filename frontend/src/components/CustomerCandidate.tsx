import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import type { CustomerCandidateItem } from "../lib/types";

interface CustomerCandidateProps {
  candidates: CustomerCandidateItem[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export function CustomerCandidateList({ candidates, selected, onSelect }: CustomerCandidateProps) {
  if (candidates.length === 0) {
    return <p className="text-one-grey text-[11px]">Nincs ugyfeltorzs-jelolt.</p>;
  }
  return (
    <ul className="divide-y divide-one-line text-[11px]">
      {candidates.map((c) => (
        <li key={c.customer_id} className="py-1.5 flex items-center justify-between gap-2">
          <label className="flex items-center gap-2 cursor-pointer min-w-0">
            <input
              type="radio"
              name="customer"
              value={c.customer_id}
              checked={selected === c.customer_id}
              onChange={() => onSelect(c.customer_id)}
              className="accent-one-turq"
            />
            <span className="truncate">
              {c.customer_name} <span className="text-one-grey">ID {c.customer_id}</span>
            </span>
          </label>
          {c.link_url?.startsWith("/") ? (
            <Link
              to={c.link_url}
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded border border-one-line text-one-turq-d hover:bg-one-turq-l"
              aria-label={`${c.customer_name} ugyfel adatlap megnyitasa`}
              title="Ugyfel adatlap"
            >
              <ExternalLink size={13} />
            </Link>
          ) : c.link_url ? (
            <a
              href={c.link_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded border border-one-line text-one-turq-d hover:bg-one-turq-l"
              aria-label={`${c.customer_name} ugyfel adatlap megnyitasa`}
              title="Ugyfel adatlap"
            >
              <ExternalLink size={13} />
            </a>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
