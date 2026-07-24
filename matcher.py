"""
A lightweight, dependency-free resume <-> job description matcher.

This is intentionally simple (keyword overlap against a curated skills
vocabulary, plus a small bonus for generic word overlap) so the whole
project runs with zero external ML services or API keys. It's meant to
be a believable v1 that's easy to explain in an interview and easy to
extend later (e.g. swap in a real NLP/embedding model without touching
the rest of the app).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A curated vocabulary of common tech/professional skills. Extend this
# list freely -- it's the whole "knowledge base" the matcher uses.
SKILLS_VOCABULARY = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "sql", "nosql", "postgresql", "mysql", "mongodb", "redis", "sqlite",
    "react", "vue", "angular", "next.js", "node.js", "express", "flask",
    "django", "fastapi", "spring", "html", "css", "tailwind", "bootstrap",
    "git", "github", "docker", "kubernetes", "aws", "azure", "gcp",
    "ci/cd", "jenkins", "terraform", "linux", "rest api", "graphql",
    "machine learning", "deep learning", "nlp", "pandas", "numpy",
    "tensorflow", "pytorch", "scikit-learn", "data analysis", "data science",
    "agile", "scrum", "jira", "figma", "ui/ux", "testing", "unit testing",
    "microservices", "system design", "communication", "leadership",
    "project management", "problem solving", "teamwork",
]

_WORD_RE = re.compile(r"[a-zA-Z\+\#\.]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on",
    "is", "are", "as", "be", "this", "that", "we", "you", "will", "our",
    "at", "by", "from", "your", "have", "has", "must", "should", "can",
}


@dataclass
class MatchResult:
    score: float
    matched_skills: list[str]
    missing_skills: list[str]


def _normalize(text: str) -> str:
    return (text or "").lower()


def _find_vocabulary_hits(text: str) -> set[str]:
    normalized = _normalize(text)
    return {skill for skill in SKILLS_VOCABULARY if skill in normalized}


def _generic_word_overlap(resume_text: str, jd_text: str) -> float:
    """A small secondary signal based on shared non-stopword tokens,
    so the score isn't purely dependent on the curated vocabulary."""
    resume_words = {w for w in _WORD_RE.findall(_normalize(resume_text)) if len(w) > 3}
    jd_words = {w for w in _WORD_RE.findall(_normalize(jd_text)) if len(w) > 3}
    resume_words -= _STOPWORDS
    jd_words -= _STOPWORDS
    if not jd_words:
        return 0.0
    overlap = resume_words & jd_words
    return len(overlap) / len(jd_words)


def match_resume_to_job(resume_text: str, job_description: str) -> MatchResult:
    if not job_description.strip():
        return MatchResult(score=0.0, matched_skills=[], missing_skills=[])

    jd_skills = _find_vocabulary_hits(job_description)
    resume_skills = _find_vocabulary_hits(resume_text)

    matched = sorted(jd_skills & resume_skills)
    missing = sorted(jd_skills - resume_skills)

    if jd_skills:
        vocab_score = len(matched) / len(jd_skills)
    else:
        vocab_score = 0.0

    generic_score = _generic_word_overlap(resume_text, job_description)

    # Weight the curated-vocabulary signal much more heavily than the
    # generic word overlap, since it's far more meaningful.
    combined = (vocab_score * 0.8) + (generic_score * 0.2)
    score = round(min(combined, 1.0) * 100, 1)

    return MatchResult(score=score, matched_skills=matched, missing_skills=missing)
