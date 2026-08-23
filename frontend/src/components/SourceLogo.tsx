// Real source logos, background-stripped, in public/logos/. Sources without
// a shipped logo (e.g. reshet13) fall back to a monogram badge below.
export const LOGO_IMAGE: Record<string, string> = {
  ynet: "/logos/ynet.png",
  haaretz: "/logos/haaretz.png",
  mako: "/logos/mako.png",
  news12: "/logos/news12.png",
  channel14: "/logos/channel14.png",
};

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
  const image = LOGO_IMAGE[source];
  if (image) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- fixed small icon, next/image overhead isn't worth it here
      <img
        src={image}
        alt=""
        className={`inline-block shrink-0 object-contain ${className}`}
        style={{ width: size, height: size }}
        aria-hidden
      />
    );
  }

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
