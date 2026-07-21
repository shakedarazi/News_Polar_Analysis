export function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-[var(--navy)]">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "radial-gradient(circle at 15% 30%, rgba(108,99,255,0.35), transparent 40%), radial-gradient(circle at 85% 20%, rgba(139,124,255,0.25), transparent 45%), radial-gradient(circle at 75% 80%, rgba(79,70,229,0.3), transparent 40%)",
        }}
        aria-hidden
      />
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full opacity-30"
        viewBox="0 0 800 400"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden
      >
        <circle cx="640" cy="180" r="90" fill="none" stroke="#8B7CFF" strokeWidth="1" />
        <circle cx="640" cy="180" r="60" fill="none" stroke="#6C63FF" strokeWidth="1" />
        {Array.from({ length: 18 }).map((_, i) => {
          const x = (i * 47) % 800;
          const y = 40 + ((i * 83) % 320);
          return <circle key={i} cx={x} cy={y} r="2" fill="#8B7CFF" opacity="0.6" />;
        })}
        <polyline
          points="20,320 120,280 220,300 320,230 420,260 520,180 620,210 720,140"
          fill="none"
          stroke="#6C63FF"
          strokeWidth="1.5"
          opacity="0.5"
        />
      </svg>

      <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:py-28">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-bold leading-tight text-white sm:text-4xl lg:text-5xl">
            הבנה עמוקה של חדשות,
            <br />
            <span className="gradient-text">מעבר לכותרות</span>
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-white/70">
            Trust מנתח כתבות ממקורות החדשות הקיימים במערכת, ומציג תובנות המבוססות
            על הנתונים שנאספו בפועל — ללא הערכות או נתונים מומצאים.
          </p>
          <a
            href="#trend"
            className="btn-primary mt-8 inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold"
          >
            גלו את המגמות
            <span aria-hidden>←</span>
          </a>
        </div>
      </div>
    </section>
  );
}
