import { ArrowLeft, Building2, Hash, Mail, MapPin, PhoneCall } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "../components/Card";
import { api } from "../lib/api";
import type { CustomerProfile as CustomerProfileType } from "../lib/types";

function DetailRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-one-line py-2 last:border-b-0">
      <span className="text-[10px] uppercase tracking-wider text-one-grey">{label}</span>
      <span className="max-w-[70%] text-right text-[12px] font-semibold text-one-ink">{value || "-"}</span>
    </div>
  );
}

export function CustomerProfile() {
  const { customerId } = useParams<{ customerId: string }>();
  const navigate = useNavigate();
  const [customer, setCustomer] = useState<CustomerProfileType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!customerId) return;
    setLoading(true);
    api
      .getCustomer(customerId)
      .then((profile) => {
        setCustomer(profile);
        setError("");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Hiba az ugyfel betoltese soran"))
      .finally(() => setLoading(false));
  }, [customerId]);

  if (loading) return <div className="text-one-grey p-8 text-center">Betoltes...</div>;
  if (error) return <div className="text-status-urgent-fg p-8">{error}</div>;
  if (!customer) return null;

  return (
    <div>
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-one-turq-d font-semibold text-[12px] hover:underline mb-3"
        aria-label="Vissza az elozo oldalra"
      >
        <ArrowLeft size={14} />
        Vissza
      </button>

      <div className="bg-gradient-to-r from-one-turq-l to-white border border-one-line rounded-one p-3 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-[18px] font-bold text-one-ink leading-snug">{customer.customer_name}</h1>
            <p className="text-[11px] text-one-grey mt-0.5">ID {customer.customer_id}</p>
          </div>
          <span className="rounded-lg border border-one-line bg-white px-2 py-1 text-[11px] font-semibold text-one-ink">
            {customer.status ?? "Ismeretlen statusz"}
          </span>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
        <div className="flex flex-col gap-3 min-w-0">
          <Card title="Alapadatok">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex items-center gap-2 rounded border border-one-line bg-one-canvas p-2">
                <Hash size={15} className="text-one-turq-d" />
                <div>
                  <p className="text-[10px] uppercase text-one-grey">Ugyfelszam</p>
                  <p className="text-[12px] font-semibold">{customer.customer_number}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded border border-one-line bg-one-canvas p-2">
                <Building2 size={15} className="text-one-turq-d" />
                <div>
                  <p className="text-[10px] uppercase text-one-grey">Szegmens</p>
                  <p className="text-[12px] font-semibold">{customer.segment ?? "-"}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded border border-one-line bg-one-canvas p-2">
                <Mail size={15} className="text-one-turq-d" />
                <div>
                  <p className="text-[10px] uppercase text-one-grey">Email</p>
                  <p className="text-[12px] font-semibold">{customer.primary_email ?? "-"}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded border border-one-line bg-one-canvas p-2">
                <MapPin size={15} className="text-one-turq-d" />
                <div>
                  <p className="text-[10px] uppercase text-one-grey">Cim</p>
                  <p className="text-[12px] font-semibold">{customer.address_masked ?? "-"}</p>
                </div>
              </div>
            </div>
          </Card>

          <Card title="Aktiv szolgaltatasok">
            <ul className="divide-y divide-one-line text-[12px]">
              {customer.services.map((service) => (
                <li key={service} className="flex items-center gap-2 py-2">
                  <PhoneCall size={14} className="text-one-turq-d" />
                  <span>{service}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <Card title="Szerzodesi osszefoglalo">
          <DetailRow label="Szolgaltato" value={customer.service_provider} />
          <DetailRow label="Szamlazasi fiok" value={customer.billing_account} />
          <DetailRow label="Szerzodes" value={customer.contract_id} />
          <DetailRow label="Preferalt csatorna" value={customer.preferred_channel} />
          <DetailRow label="Ugyfel kezdete" value={customer.since} />
          <div className="pt-3">
            <p className="text-[10px] uppercase tracking-wider text-one-grey">Megjegyzes</p>
            <p className="mt-1 text-[12px] leading-relaxed text-one-ink">{customer.notes ?? "-"}</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
