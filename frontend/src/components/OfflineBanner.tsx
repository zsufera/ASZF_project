export function OfflineBanner({ offline }: { offline: boolean }) {
  if (!offline) return null;
  return (
    <div className="bg-status-esc-bg border-b border-status-esc-fg text-status-esc-fg text-[11px] font-semibold px-4 py-2 text-center" role="alert">
      ⚠ Backend offline — az adatok nem tölthetők.
    </div>
  );
}
