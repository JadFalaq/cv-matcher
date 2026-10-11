const BACKGROUNDS = { white: "bg-white", muted: "bg-slate-50", accent: "bg-indigo-50/60" };

/** Section de la page d'accueil : surtitre, titre, introduction, contenu. */
export default function Section({
  id,
  eyebrow,
  title,
  intro,
  tone = "white",
  children,
}: {
  id?: string;
  eyebrow: string;
  title: string;
  intro?: React.ReactNode;
  tone?: "white" | "muted" | "accent";
  children: React.ReactNode;
}) {
  return (
    <section id={id} className={`scroll-mt-20 py-16 sm:py-20 ${BACKGROUNDS[tone]}`}>
      <div className="mx-auto max-w-6xl px-4">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-indigo-600">{eyebrow}</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">{title}</h2>
          {intro && <p className="mt-4 text-lg text-slate-600">{intro}</p>}
        </div>
        <div className="mt-12">{children}</div>
      </div>
    </section>
  );
}
