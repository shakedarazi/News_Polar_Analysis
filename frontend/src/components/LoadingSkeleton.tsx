export function LoadingSkeleton({ className = "h-40" }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="טוען נתונים"
      className={`card animate-pulse bg-slate-100 ${className}`}
    />
  );
}

export function StatsGridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <LoadingSkeleton key={i} className="h-28" />
      ))}
    </div>
  );
}
