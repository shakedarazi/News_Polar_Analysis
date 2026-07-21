import { Newspaper } from "lucide-react";
import { placeholderGradient } from "@/lib/format";

export function ArticleThumbnail({ seed, className = "" }: { seed: string; className?: string }) {
  const [from, to] = placeholderGradient(seed);
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-xl ${className}`}
      style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}
      role="img"
      aria-label="תמונה ממלאת מקום — לא זמינה תמונת כתבה"
    >
      <Newspaper className="h-6 w-6 text-white/80" aria-hidden />
    </div>
  );
}
