"""
Skill extraction and normalization service using spaCy and a configurable technical skill dictionary.
"""
import re
from typing import List, Dict, Set
import spacy

# Load spaCy pipeline for tokenization and entity recognition
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")

# Comprehensive Canonical Skill Taxonomy with variations & normalization mappings
SKILL_TAXONOMY: Dict[str, List[str]] = {
    # Programming Languages
    "Python": ["python", "py"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "Java": ["java", "core java", "j2se"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", "c sharp"],
    "C": ["c language"],
    "Go": ["golang", "go language"],
    "Rust": ["rust", "rustlang"],
    "Ruby": ["ruby"],
    "PHP": ["php"],
    "Swift": ["swift"],
    "Kotlin": ["kotlin"],
    "SQL": ["sql", "structured query language"],
    "R": ["r programming", "r language"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "Bash": ["bash", "shell scripting", "powershell"],

    # Frontend Frameworks & Libraries
    "React": ["react", "react.js", "reactjs"],
    "Next.js": ["next.js", "nextjs", "next"],
    "Vue.js": ["vue", "vue.js", "vuejs"],
    "Angular": ["angular", "angular.js", "angularjs"],
    "Tailwind CSS": ["tailwind", "tailwindcss", "tailwind css"],
    "Bootstrap": ["bootstrap", "bootstrap5"],
    "Redux": ["redux", "redux toolkit"],

    # Backend Frameworks
    "FastAPI": ["fastapi", "fast api"],
    "Django": ["django", "django rest framework", "drf"],
    "Flask": ["flask"],
    "Node.js": ["node.js", "nodejs", "node js"],
    "Express.js": ["express", "express.js", "expressjs"],
    "Spring Boot": ["spring boot", "springboot", "spring framework"],
    "ASP.NET": ["asp.net", "asp.net core", ".net core", "dotnet"],

    # Databases & Caches
    "MySQL": ["mysql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "SQLite": ["sqlite", "sqlite3"],
    "Elasticsearch": ["elasticsearch", "elastic search"],
    "Firebase": ["firebase", "firestore"],
    "Oracle Database": ["oracle db", "oracle sql"],

    # Cloud & DevOps
    "Amazon Web Services (AWS)": ["aws", "amazon web services", "aws ec2", "aws s3", "aws lambda"],
    "Google Cloud Platform (GCP)": ["gcp", "google cloud", "google cloud platform"],
    "Microsoft Azure": ["azure", "microsoft azure"],
    "Docker": ["docker", "dockerfile", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "CI/CD": ["ci/cd", "ci cd", "continuous integration", "github actions", "gitlab ci", "jenkins"],
    "Git": ["git", "github", "gitlab"],
    "Terraform": ["terraform"],
    "Linux": ["linux", "ubuntu", "debian", "centos", "redhat"],
    "Nginx": ["nginx"],

    # Machine Learning & AI
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "dl", "neural networks"],
    "Natural Language Processing (NLP)": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision", "cv", "opencv"],
    "Large Language Models (LLMs)": ["llm", "llms", "large language models", "prompt engineering"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow", "tf"],
    "Scikit-Learn": ["scikit-learn", "sklearn", "scikit learn"],
    "spaCy": ["spacy"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],

    # Software Engineering & Methodologies
    "REST API": ["rest", "restful", "rest api", "restful api", "rest apis"],
    "GraphQL": ["graphql"],
    "Microservices": ["microservices", "microservice architecture"],
    "Agile": ["agile", "scrum", "kanban", "sprints"],
    "Object-Oriented Programming (OOP)": ["oop", "object oriented programming"],
    "Data Structures & Algorithms": ["dsa", "data structures", "algorithms"],
    "Unit Testing": ["unit testing", "pytest", "jest", "junit", "test driven development", "tdd"],
}


def build_alias_to_canonical_map() -> Dict[str, str]:
    """
    Constructs an inverted lookup index mapping lowercase variations to canonical skill names.
    """
    alias_map: Dict[str, str] = {}
    for canonical, aliases in SKILL_TAXONOMY.items():
        # Canonical name itself is an alias
        alias_map[canonical.lower()] = canonical
        for alias in aliases:
            alias_map[alias.lower()] = canonical
    return alias_map


ALIAS_TO_CANONICAL = build_alias_to_canonical_map()


def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract technical skills from text using boundary-safe matching and alias normalization.
    Preserves unique skills in order of discovery.
    """
    if not text:
        return []

    found_canonical_skills: Set[str] = set()
    ordered_skills: List[str] = []
    text_lower = text.lower()

    # Sort aliases by descending length so multi-word skills (e.g. 'spring boot') match before 'spring'
    sorted_aliases = sorted(ALIAS_TO_CANONICAL.keys(), key=lambda a: len(a), reverse=True)

    for alias in sorted_aliases:
        # Match using word boundaries or symbol boundaries for skills like c++, c#, .net
        escaped_alias = re.escape(alias)
        pattern = rf"(?<![\w#+]){escaped_alias}(?![\w#+])"

        if re.search(pattern, text_lower):
            canonical = ALIAS_TO_CANONICAL[alias]
            if canonical not in found_canonical_skills:
                found_canonical_skills.add(canonical)
                ordered_skills.append(canonical)

    return ordered_skills
