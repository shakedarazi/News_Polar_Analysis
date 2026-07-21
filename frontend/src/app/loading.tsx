import { LoadingSkeleton, StatsGridSkeleton } from "@/components/LoadingSkeleton";

export default function Loading() {
  return (
    <div>
      <div className="h-80 animate-pulse bg-[var(--navy)]" role="status" aria-label="טוען" />
      <div className="mx-auto max-w-7xl space-y-10 px-4 py-10 sm:px-6">
        <StatsGridSkeleton />
        <LoadingSkeleton className="h-80" />
        <LoadingSkeleton className="h-64" />
      </div>
    </div>
  );
}
