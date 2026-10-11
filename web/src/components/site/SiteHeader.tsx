const NAV = [
  { href: "#fonctionnement", label: "Comment ça marche" },
  { href: "#situations", label: "Lire son bilan" },
  { href: "#garanties", label: "Garanties" },
  { href: "#faq", label: "FAQ" },
];

export default function SiteHeader({ landing, onHome }: { landing: boolean; onHome: () => void }) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <button onClick={onHome} className="flex items-center gap-2 text-lg font-semibold text-slate-900">
          <span aria-hidden className="grid size-8 place-items-center rounded-lg bg-indigo-600 text-sm text-white">
            cv
          </span>
          cvmatch
        </button>
        {landing ? (
          <nav className="flex items-center gap-1 text-sm">
            {NAV.map((n) => (
              <a
                key={n.href}
                href={n.href}
                className="hidden rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 md:block"
              >
                {n.label}
              </a>
            ))}
            <a href="#analyser" className="ml-2 rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-500">
              Analyser mon CV
            </a>
          </nav>
        ) : (
          <button
            onClick={onHome}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
          >
            Nouvelle analyse
          </button>
        )}
      </div>
    </header>
  );
}
