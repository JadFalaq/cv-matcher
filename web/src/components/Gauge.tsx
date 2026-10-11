/** Jauge circulaire du score sur 100. */
export default function Gauge({ value, size = "size-36" }: { value: number; size?: string }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const color = value >= 55 ? "stroke-emerald-500" : value >= 35 ? "stroke-amber-400" : "stroke-rose-500";
  return (
    <div className={`relative ${size} shrink-0`}>
      <svg viewBox="0 0 120 120" className="size-full -rotate-90" aria-hidden>
        <circle cx="60" cy="60" r={r} fill="none" strokeWidth="12" className="stroke-slate-100" />
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          strokeWidth="12"
          strokeLinecap="round"
          className={color}
          strokeDasharray={c}
          strokeDashoffset={c * (1 - Math.min(value, 100) / 100)}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <span className="text-4xl font-bold text-slate-900">{Math.round(value)}</span>
          <span className="block text-sm text-slate-500">sur 100</span>
        </div>
      </div>
    </div>
  );
}
