import type { CustomerCandidateItem } from "../lib/types";

interface CustomerCandidateProps {
  candidates: CustomerCandidateItem[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export function CustomerCandidateList({ candidates, selected, onSelect }: CustomerCandidateProps) {
  if (candidates.length === 0) {
    return <p className="text-one-grey text-[11px]">Nincs ügyféltörzs-jelölt.</p>;
  }
  return (
    <ul className="divide-y divide-one-line text-[11px]">
      {candidates.map((c) => (
        <li key={c.customer_id} className="py-1.5 flex items-center justify-between gap-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="customer"
              value={c.customer_id}
              checked={selected === c.customer_id}
              onChange={() => onSelect(c.customer_id)}
              className="accent-one-turq"
            />
            <span>{c.customer_name} · <span className="text-one-grey">ID {c.customer_id}</span></span>
          </label>
          {c.link_url && (
            <a
              href={c.link_url}
              target="_blank"
              rel="noreferrer"
              className="text-one-turq-d hover:underline text-[10px]"
              aria-label="Megnyitás"
            >
              ⤴
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
