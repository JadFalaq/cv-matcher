import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "cvmatch : adapte ton CV à une offre",
  description:
    "Pour chaque compétence d'une offre d'emploi, cvmatch vérifie si ton CV la prouve, propose des reformulations de tes propres lignes et liste honnêtement ce qui manque.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
