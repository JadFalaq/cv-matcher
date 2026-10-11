import { ChevronRight } from "lucide-react";

import { FAQ } from "@/lib/faq";

export default function Faq() {
  return (
    <div className="mx-auto max-w-3xl divide-y divide-slate-200 rounded-2xl bg-white ring-1 ring-slate-200">
      {FAQ.map((f) => (
        <details key={f.q} className="group px-5 py-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-medium text-slate-900">
            {f.q}
            <ChevronRight className="size-4 shrink-0 text-slate-400 transition group-open:rotate-90" aria-hidden />
          </summary>
          <p className="mt-2 text-slate-600">{f.a}</p>
        </details>
      ))}
    </div>
  );
}
