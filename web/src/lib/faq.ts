export const FAQ = [
  {
    q: "Est-ce gratuit ? Faut-il créer un compte ?",
    a: "C'est gratuit et sans inscription. Pour que le service reste disponible pour tout le monde, le nombre d'analyses est limité à quelques-unes par heure et par personne.",
  },
  {
    q: "Que devient mon CV ?",
    a: "Il est lu, analysé, puis oublié : rien n'est enregistré sur nos serveurs. Le texte est transmis à un modèle d'IA (Azure OpenAI) uniquement le temps de l'analyse. Évite tout de même d'y laisser des informations très sensibles (numéro de sécurité sociale, adresse complète…).",
  },
  {
    q: "Pourquoi distinguer « bien visible » et « avec d'autres mots » ?",
    a: "Beaucoup d'entreprises trient les candidatures avec un logiciel qui cherche les mots exacts de l'offre, et un recruteur parcourt souvent un CV en quelques secondes. Si tu écris « apprentissage profond » alors que l'offre dit « deep learning », ta compétence risque de passer inaperçue.",
  },
  {
    q: "Les reformulations peuvent-elles inventer quelque chose ?",
    a: "Non. Chaque reformulation est contrôlée par un programme : elle doit partir d'une vraie ligne de ton CV, ne peut ajouter ni chiffre ni outil qui n'y figure pas, et doit rester de longueur proche. Celles qui ne passent pas ces contrôles sont écartées.",
  },
  {
    q: "Comment savoir si une preuve est fiable ?",
    a: "Chaque citation affichée a été retrouvée mot pour mot dans ton CV. Quand l'IA et les contrôles ne sont pas d'accord, la compétence est marquée « à vérifier » : relis-la toi-même.",
  },
  {
    q: "Une compétence « absente » que je possède vraiment ?",
    a: "Cela veut dire qu'aucune ligne de ton CV ne la montre. Si tu l'as, ajoute une ligne concrète qui la prouve (un projet, une mission). Si tu ne l'as pas, ne l'ajoute pas : un mini-projet ou une courte formation sont de meilleures réponses.",
  },
  {
    q: "Ça marche pour tous les métiers ?",
    a: "Oui : l'analyse fonctionne pour n'importe quelle offre (comptabilité, marketing, santé, technique…). Elle est un peu plus fine pour les métiers de la data et de l'IA, pour lesquels l'outil connaît en plus les synonymes et les outils courants.",
  },
  {
    q: "Mon CV est en PDF à deux colonnes, est-ce un problème ?",
    a: "Le texte des PDF à plusieurs colonnes est parfois extrait dans le désordre, ce qui peut gêner l'analyse. Si le résultat te semble étrange, colle simplement le texte de ton CV dans l'onglet « Texte ». Un PDF scanné (une image) ne contient pas de texte lisible.",
  },
  {
    q: "Le score garantit-il un entretien ?",
    a: "Non. Il mesure à quel point ton CV montre ce que l'offre demande, avec ses mots. C'est un outil pour rendre ton CV plus lisible, pas une prédiction de recrutement.",
  },
];
