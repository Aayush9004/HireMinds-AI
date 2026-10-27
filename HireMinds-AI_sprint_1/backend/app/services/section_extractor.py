"""
Section extraction service for Education, Work Experience, and Projects from resume text.
Uses regular expressions, section header parsing, and rule-based heuristics.
"""
import re
from typing import List, Dict, Any, Optional

DEGREE_PATTERNS = [
    r"\b(?:B\.?Tech|Bachelor of Technology)\b",
    r"\b(?:B\.?E\.?|Bachelor of Engineering)\b",
    r"\b(?:B\.?S\.?c?|Bachelor of Science)\b",
    r"\b(?:B\.?C\.?A\.?|Bachelor of Computer Applications)\b",
    r"\b(?:M\.?Tech|Master of Technology)\b",
    r"\b(?:M\.?S\.?c?|Master of Science)\b",
    r"\b(?:M\.?C\.?A\.?|Master of Computer Applications)\b",
    r"\b(?:Ph\.?D\.?|Doctor of Philosophy)\b",
    r"\b(?:Diploma in [A-Za-z\s]+)\b",
    r"\b(?:Bachelor['’]?s|Master['’]?s)\b",
]

YEAR_PATTERN = r"\b(19\d{2}|20\d{2})\b"
CGPA_PATTERN = r"\b(?:CGPA|GPA|Percentage)?\s*[:=-]?\s*(\d{1,2}(?:\.\d{1,2})?)\s*(?:/|out of)?\s*(?:10|100|4\.0)?\b"


def extract_education(text: str) -> List[Dict[str, Any]]:
    """
    Extract educational credentials, institutions, and graduation years.
    """
    education_records = []
    lines = text.splitlines()

    for i, line in enumerate(lines):
        for pattern in DEGREE_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                degree = match.group(0).strip()
                # Search nearby context (+/- 2 lines) for institution and year
                context_lines = lines[max(0, i - 1):min(len(lines), i + 3)]
                context_str = " ".join(context_lines)

                years = re.findall(YEAR_PATTERN, context_str)
                grad_year = years[-1] if years else None

                cgpa_match = re.search(CGPA_PATTERN, context_str, re.IGNORECASE)
                cgpa = cgpa_match.group(1) if cgpa_match else None

                education_records.append({
                    "degree": degree,
                    "institution_context": line.strip(),
                    "year": grad_year,
                    "grade_or_cgpa": cgpa,
                })
                break

    # If no explicit degree pattern matched, search for educational keywords
    if not education_records and re.search(r"\b(University|Institute|College|School|Academy)\b", text, re.IGNORECASE):
        for line in lines:
            if re.search(r"\b(University|Institute|College)\b", line, re.IGNORECASE):
                education_records.append({
                    "degree": "Higher Education",
                    "institution_context": line.strip(),
                    "year": None,
                    "grade_or_cgpa": None,
                })
                break

    return education_records


def extract_experience(text: str) -> Dict[str, Any]:
    """
    Estimate professional experience, identify job titles, and extract experience snippets.
    """
    job_title_patterns = [
        r"\b(?:Senior|Junior|Lead|Principal)?\s*(?:Software|Frontend|Backend|Full[\s-]Stack|DevOps|Data|Machine Learning|AI|QA|Cloud)?\s*(?:Engineer|Developer|Architect|Scientist|Consultant|Intern|Specialist)\b",
        r"\b(?:Product|Project|Technical)?\s*Manager\b",
        r"\b(?:Data|Business|System)\s*Analyst\b",
    ]

    identified_roles = []
    lines = text.splitlines()

    for line in lines:
        for pattern in job_title_patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for m in matches:
                role = m.group(0).strip()
                if len(role) > 3 and role not in identified_roles:
                    identified_roles.append(role)

    # Heuristic: Extract years of experience mentions like "3+ years of experience" or "2 years working with"
    exp_year_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s*(?:of)?\s*(?:experience|working)?", text, re.IGNORECASE)
    estimated_years: Optional[float] = None
    if exp_year_match:
        try:
            estimated_years = float(exp_year_match.group(1))
        except ValueError:
            pass

    return {
        "estimated_years": estimated_years,
        "identified_roles": identified_roles[:5],  # top identified roles
        "has_internship": bool(re.search(r"\bintern(?:ship)?\b", text, re.IGNORECASE)),
    }


def extract_projects(text: str) -> List[Dict[str, Any]]:
    """
    Extract personal, academic, or professional projects mentioned in resume text.
    """
    projects = []
    lines = text.splitlines()

    in_project_section = False
    current_project = None

    project_header_pattern = re.compile(r"^(?:projects?|key projects?|academic projects?|personal projects?)[:\s]*$", re.IGNORECASE)
    section_break_pattern = re.compile(r"^(?:education|experience|skills|certifications|awards|interests|summary)[:\s]*$", re.IGNORECASE)

    for line in lines:
        clean = line.strip()
        if not clean:
            continue

        if project_header_pattern.match(clean):
            in_project_section = True
            continue

        if in_project_section:
            if section_break_pattern.match(clean):
                in_project_section = False
                if current_project:
                    projects.append(current_project)
                    current_project = None
                break

            # Project title line heuristic (e.g. bold or starting line without bullet or contains tech stack)
            if not clean.startswith(("-", "•", "*", "–")) and len(clean) < 80:
                if current_project:
                    projects.append(current_project)
                current_project = {
                    "title": clean,
                    "description": [],
                }
            elif current_project:
                current_project["description"].append(clean.lstrip("-•*– "))

    if current_project:
        projects.append(current_project)

    # Format project descriptions into unified strings
    formatted_projects = []
    for p in projects[:6]:
        formatted_projects.append({
            "title": p["title"],
            "description": " ".join(p["description"]) if p["description"] else p["title"],
        })

    return formatted_projects
