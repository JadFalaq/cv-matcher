import type { Assessment, Importance, Status } from "./types";

/** Les 4 situations possibles d'une compétence, en langage simple. */
export const STATUS_INFO: Record<
  Status,
  { title: string; short: string; explain: string; action: string; dot: string; badge: string; card: string }
> = {
  visible: {
    title: "Bien visible",
    short: "Visible",
    explain: "Ton CV emploie les mêmes mots que l'offre. Un recruteur ou un logiciel de tri la repère tout de suite.",
    action: "Rien à faire.",
    dot: "bg-emerald-500",
    badge: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    card: "border-emerald-200",
  },
  hidden: {
    title: "Présente, mais avec d'autres mots",
    short: "Mots différents",
    explain:
      "Tu as bien cette compétence, mais ton CV la décrit autrement que l'offre (par exemple « apprentissage profond » au lieu de « deep learning »). Un tri par mots-clés peut la manquer.",
    action: "Reprends les mots exacts de l'offre : on te propose une reformulation.",
    dot: "bg-amber-400",
    badge: "bg-amber-50 text-amber-800 ring-amber-200",
    card: "border-amber-200",
  },
  implicit: {
    title: "Présente, mais pas écrite",
    short: "Sous-entendue",
    explain:
      "La compétence se déduit d'un outil ou d'un projet de ton CV (par exemple FastAPI implique « API REST »), sans être nommée. Un lecteur pressé ne fera pas le lien.",
    action: "Nomme-la explicitement : on te propose une reformulation.",
    dot: "bg-orange-500",
    badge: "bg-orange-50 text-orange-800 ring-orange-200",
    card: "border-orange-200",
  },
  absent: {
    title: "Pas trouvée dans ton CV",
    short: "Absente",
    explain: "Aucune ligne de ton CV ne montre cette compétence.",
    action: "Ne l'invente pas. Si tu l'as vraiment, ajoute une ligne qui le prouve ; sinon, c'est une piste de progression.",
    dot: "bg-rose-500",
    badge: "bg-rose-50 text-rose-800 ring-rose-200",
    card: "border-rose-200",
  },
};

export const STATUS_ORDER: Status[] = ["visible", "hidden", "implicit", "absent"];

/** « 1 visible », « 4 sous-entendues », « 6 absentes »… */
export function statusCount(status: Status, n: number): string {
  const plural = n > 1 ? "s" : "";
  const words: Record<Status, string> = {
    visible: `visible${plural}`,
    hidden: "avec d'autres mots",
    implicit: `sous-entendue${plural}`,
    absent: `absente${plural}`,
  };
  return `${n} ${words[status]}`;
}

/** Première lettre en majuscule, sans toucher au reste (« MLOps », « API REST »). */
export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const IMPORTANCE_LABEL: Record<Importance, string> = {
  must: "Indispensable",
  nice: "Un plus",
};

/** Nom affiché : le terme tel qu'il est écrit dans l'offre (« API REST »), sinon le nom normalisé. */
export function skillName(a: Assessment): string {
  return capitalize(a.requirement.offer_terms[0] ?? a.requirement.name);
}

/** Lecture du score en une phrase. */
export function scoreVerdict(score: number): { label: string; text: string; tone: string } {
  if (score >= 75)
    return {
      label: "Très bon match",
      text: "Ton CV montre clairement la plupart de ce que demande l'offre.",
      tone: "text-emerald-700",
    };
  if (score >= 55)
    return {
      label: "Bon match, à affiner",
      text: "L'essentiel est là, mais une partie est mal mise en valeur. Les reformulations ci-dessous peuvent faire la différence.",
      tone: "text-emerald-700",
    };
  if (score >= 35)
    return {
      label: "Match partiel",
      text: "Une partie des attentes est couverte. Commence par les reformulations, puis regarde les compétences manquantes.",
      tone: "text-amber-700",
    };
  return {
    label: "Match faible",
    text: "Beaucoup d'attentes de l'offre n'apparaissent pas dans ton CV. Vérifie que l'offre correspond bien à ton profil.",
    tone: "text-rose-700",
  };
}
