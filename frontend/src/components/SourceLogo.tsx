// NOTE: real news-outlet logos are trademarked brand assets we don't have
// rights to embed/redistribute, so this renders a distinct monogram badge
// per source instead of the actual site logo.
export const LOGO_TEXT: Record<string, string> = {
  ynet: "YN",
  haaretz: "הא",
  mako: "מק",
  news12: "12",
  reshet13: "13",
  channel14: "14",
};

export const LOGO_COLOR: Record<string, string> = {
  ynet: "#DC2626",
  haaretz: "#334155",
  mako: "#16A34A",
  news12: "#2563EB",
  reshet13: "#9333EA",
  channel14: "#EA580C",
};

export function SourceLogo({
  source,
  size = 22,
  className = "",
}: {
  source: string;
  size?: number;
  className?: string;
}) {
  const text = LOGO_TEXT[source] ?? source.slice(0, 2).toUpperCase();
  const color = LOGO_COLOR[source] ?? "#64748B";
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-bold leading-none text-white ${className}`}
      style={{ width: size, height: size, background: color, fontSize: size * 0.38 }}
      aria-hidden
    >
      {text}
    </span>
  );
}
