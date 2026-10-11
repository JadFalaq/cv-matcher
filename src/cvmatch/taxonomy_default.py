"""Mini-référentiel de compétences (FR/EN) pour le profil IA / data / MLOps.

Chaque entrée : (nom canonique, catégorie, alias, déclencheurs « implicites »).

- alias       : autres façons d'écrire la même compétence (synonymes, traductions).
- implied_by  : mots qui, présents dans un CV, *impliquent* la compétence sans la nommer
                (ex. « FastAPI » implique « API REST »).

Pour passer à l'échelle, charge ESCO ou ta propre liste avec `Taxonomy.from_json(...)`.
"""

DEFAULT_SKILLS = [
    # ---- IA / ML
    ("python", "technical", ["python3", "python 3"], ["pandas", "numpy", "pytorch", "fastapi", "flask", "jupyter"]),
    ("machine learning", "technical", ["ML", "apprentissage automatique", "apprentissage statistique"],
     ["scikit-learn", "xgboost", "random forest", "régression logistique", "svm"]),
    ("deep learning", "technical", ["apprentissage profond", "réseaux de neurones"],
     ["pytorch", "tensorflow", "cnn", "lstm", "resnet"]),
    ("computer vision", "technical", ["vision par ordinateur", "vision artificielle"],
     ["yolo", "opencv", "détection d'objets", "segmentation d'images", "classification d'images"]),
    ("nlp", "technical", ["traitement du langage naturel", "natural language processing"],
     ["tokenisation", "analyse de sentiments", "bert"]),
    ("llm", "technical", ["large language model", "large language models", "grands modèles de langage", "modèles de langage"],
     ["gpt-4", "gpt-4o", "llama", "mistral", "azure openai", "openai api"]),
    ("generative ai", "technical", ["genai", "gen ai", "ia générative", "intelligence artificielle générative"],
     ["chatgpt", "stable diffusion", "dall-e"]),
    ("rag", "technical", ["retrieval augmented generation", "retrieval-augmented generation", "génération augmentée par récupération"],
     ["chatbot documentaire", "recherche sémantique", "faiss", "chroma"]),
    ("langchain", "tool", [], ["lcel"]),
    ("langgraph", "tool", [], ["stategraph"]),
    ("agentic ai", "technical", ["agents ia", "ia agentique", "systèmes agentiques", "ai agents", "agents autonomes", "multi-agent", "multi-agents"],
     ["tool calling", "function calling", "react agent", "autogen", "crewai"]),
    ("prompt engineering", "technical", ["ingénierie de prompts", "conception de prompts"], ["few-shot", "chain-of-thought"]),
    ("fine-tuning", "technical", ["fine tuning", "finetuning", "ajustement fin", "lora", "qlora"], ["peft"]),
    ("vector databases", "technical",
     ["base de données vectorielle", "bases de données vectorielles", "vector database", "vector store", "vector stores", "vectordb"],
     ["faiss", "chroma", "pinecone", "qdrant", "weaviate", "pgvector"]),
    ("embeddings", "technical", ["plongements", "word embeddings", "sentence embeddings"], ["sentence-transformers", "word2vec"]),
    ("statistics", "technical", ["statistiques", "statistique", "analyse statistique"], ["tests d'hypothèses", "probabilités"]),
    ("data visualization", "technical", ["visualisation de données", "dataviz", "data viz"], ["matplotlib", "seaborn", "plotly"]),
    # ---- frameworks / bibliothèques
    ("pytorch", "tool", ["torch"], []),
    ("tensorflow", "tool", ["keras"], []),
    ("scikit-learn", "tool", ["sklearn", "scikit learn"], []),
    ("pandas", "tool", [], ["dataframe"]),
    ("numpy", "tool", [], []),
    ("opencv", "tool", ["open cv"], []),
    ("yolo", "tool", ["yolov8", "yolov5", "yolov11"], []),
    ("hugging face", "tool", ["huggingface"], ["from_pretrained"]),
    # ---- MLOps / DevOps / cloud
    ("mlops", "technical", ["ml ops", "machine learning operations"], ["mlflow", "dvc", "model registry", "kubeflow"]),
    ("mlflow", "tool", [], []),
    ("airflow", "tool", ["apache airflow"], ["dag"]),
    ("docker", "tool", ["conteneurisation", "containers", "docker compose"], ["dockerfile"]),
    ("kubernetes", "tool", ["k8s"], ["helm"]),
    ("ci/cd", "technical", ["cicd", "intégration continue", "déploiement continu", "pipelines ci"],
     ["github actions", "gitlab ci", "jenkins"]),
    ("git", "tool", ["gitlab"], ["pull request", "github"]),
    ("linux", "tool", ["unix", "bash"], ["shell scripting"]),
    ("azure", "tool", ["microsoft azure", "azure cloud"], ["azure openai", "azure devops", "azure functions"]),
    ("aws", "tool", ["amazon web services"], ["sagemaker", "ec2"]),
    ("gcp", "tool", ["google cloud", "google cloud platform"], ["bigquery", "vertex ai"]),
    # ---- backend / données
    ("fastapi", "tool", [], ["uvicorn"]),
    ("flask", "tool", [], []),
    ("rest api", "technical", ["api rest", "restful", "apis rest", "api restful", "rest apis", "web services rest"],
     ["fastapi", "flask", "endpoints", "swagger", "openapi"]),
    ("sql", "technical", ["requêtes sql"], ["postgresql", "mysql", "sqlite"]),
    ("postgresql", "tool", ["postgres"], []),
    ("mongodb", "tool", ["nosql"], []),
    ("data engineering", "technical", ["ingénierie des données", "etl", "elt", "pipelines de données"],
     ["airflow", "spark", "kafka", "data pipeline"]),
    ("apache spark", "tool", ["spark", "pyspark"], []),
    ("kafka", "tool", ["apache kafka"], []),
    ("power bi", "tool", ["powerbi"], []),
    # ---- web / autres langages
    ("javascript", "technical", ["ecmascript"], ["node.js"]),
    ("typescript", "technical", [], []),
    ("react", "tool", ["react.js", "reactjs"], []),
    ("next.js", "tool", ["nextjs", "next js"], []),
    ("java", "technical", [], ["spring boot", "maven"]),
    ("c++", "technical", ["cpp"], []),
    # ---- méthodes / outils de gestion
    ("jira", "tool", [], []),
    ("agile", "technical", ["scrum", "méthodes agiles", "méthode agile", "kanban"], ["sprints", "daily meeting"]),
    # ---- langues & compétences comportementales
    ("english", "language", ["anglais"], []),
    ("french", "language", ["français"], []),
    ("teamwork", "soft", ["travail en équipe", "esprit d'équipe", "collaboration"], ["projet d'équipe", "travail collaboratif"]),
    ("communication", "soft", ["communication orale", "communication écrite", "sens de la communication"],
     ["présentation orale", "soutenance"]),
    ("autonomy", "soft", ["autonomie", "esprit d'initiative", "proactivité"], []),
    ("problem solving", "soft", ["résolution de problèmes", "esprit analytique"], []),
]
