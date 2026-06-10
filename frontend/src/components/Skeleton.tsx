function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`bg-one-line rounded animate-pulse ${className}`} />;
}

export function InboxSkeleton() {
  return (
    <div className="flex flex-col gap-2" aria-busy="true" aria-label="Betöltés...">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="bg-one-surface border border-one-line rounded-one shadow-card p-3 flex items-start gap-3">
          <SkeletonBlock className="w-4 h-4 mt-1 shrink-0" />
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex gap-2">
              <SkeletonBlock className="h-4 w-16" />
              <SkeletonBlock className="h-4 w-12" />
              <SkeletonBlock className="h-4 w-10" />
            </div>
            <SkeletonBlock className={`h-4 ${i % 2 === 0 ? "w-2/3" : "w-1/2"}`} />
            <SkeletonBlock className="h-3 w-32" />
          </div>
          <SkeletonBlock className="h-7 w-20 rounded-pill shrink-0" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one p-4 space-y-3" aria-busy="true">
      <SkeletonBlock className="h-4 w-32" />
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonBlock key={i} className={`h-3 ${i % 3 === 0 ? "w-full" : i % 3 === 1 ? "w-4/5" : "w-2/3"}`} />
      ))}
    </div>
  );
}
