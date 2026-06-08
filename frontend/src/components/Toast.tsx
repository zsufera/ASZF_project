import { useToast } from "../state/toast";

const COLORS = {
  success: "bg-kpi-ok text-white",
  error: "bg-kpi-bad text-white",
  info: "bg-one-turq text-[#04201f]",
};

export function ToastContainer() {
  const { toasts } = useToast();
  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`px-4 py-2 rounded-pill text-[12px] font-semibold shadow-lg animate-fade-up pointer-events-auto ${COLORS[t.kind]}`}
          role="status"
          aria-live="polite"
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
