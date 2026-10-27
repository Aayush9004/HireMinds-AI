"""
Phase 7 unit tests: explainable ATS scoring, missing-data handling and ranking.

These tests are deliberately hermetic:
* No database connection is required.
* The semantic model is mocked, so no model download or inference is needed.
* ORM objects are replaced with simple MagicMock objects carrying only the
  attributes the scoring functions read.

The tests verify:
* the weighted formula and normalisation to 0-100
* renormalisation when a component is missing (missing is NOT zero)
* all five component calculations and edge cases
* evidence generation for skills and experience
* ranking order, tie-breakers and unscored candidates
* configurable weights and their validation
* fairness-oriented text sanitisation
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.services import ats_service


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def make_resume(
    *,
    raw_text: str = "Python developer with FastAPI experience.",
    skills=None,
    education=None,
    experience=None,
    projects=None,
    reviewed: bool = False,
    corrected=None,
):
    resume = MagicMock()
    resume.id = 1
    resume.user_id = 10
    resume.raw_text = raw_text
    resume.extracted_skills = skills if skills is not None else ["Python", "FastAPI"]
    resume.extracted_education = education if education is not None else []
    resume.extracted_experience = experience if experience is not None else {}
    resume.extracted_projects = projects if projects is not None else []
    resume.is_reviewed_by_candidate = reviewed
    resume.candidate_corrected_data = corrected
    return resume


def make_job(
    *,
    title: str = "Python Developer",
    description: str = "Build Python and FastAPI services.",
    required=None,
    preferred=None,
    min_years: float = 2.0,
    education: str = "Bachelor's Degree",
):
    job = MagicMock()
    job.id = 2
    job.title = title
    job.company_name = "TechCorp"
    job.description = description
    job.required_skills = required if required is not None else ["Python", "FastAPI"]
    job.preferred_skills = preferred if preferred is not None else ["Docker"]
    job.min_experience_years = min_years
    job.required_education = education
    return job


def component(key, weight, score, status="scored", missing=None, dq="candidate_reviewed"):
    return ats_service._make_component(
        key,
        weight,
        score,
        status,
        "test component",
        missing=missing or [],
        data_quality=dq,
    )


ALL_COMPONENT_PATCHES = [
    "app.services.ats_service.score_skill_component",
    "app.services.ats_service.score_experience_component",
    "app.services.ats_service.score_education_component",
    "app.services.ats_service.score_project_component",
    "app.services.ats_service.score_semantic_component",
]


# --------------------------------------------------------------------------- #
# Formula and aggregation                                                      #
# --------------------------------------------------------------------------- #
class TestAtsFormula:
    def test_all_components_use_configured_weights(self):
        weights = ats_service.get_weights()
        returns = [
            component("skills", weights["skills"], 80),
            component("experience", weights["experience"], 60),
            component("education", weights["education"], 70),
            component("projects", weights["projects"], 50),
            component("semantic", weights["semantic"], 90, dq="model_generated"),
        ]
        with patch(ALL_COMPONENT_PATCHES[0], return_value=returns[0]), \
             patch(ALL_COMPONENT_PATCHES[1], return_value=returns[1]), \
             patch(ALL_COMPONENT_PATCHES[2], return_value=returns[2]), \
             patch(ALL_COMPONENT_PATCHES[3], return_value=returns[3]), \
             patch(ALL_COMPONENT_PATCHES[4], return_value=returns[4]):
            result = ats_service.compute_ats_score(make_resume(), make_job())

        # 0.40*80 + 0.25*60 + 0.15*70 + 0.10*50 + 0.10*90 = 71.5
        assert result["ats_score"] == pytest.approx(71.5, abs=0.01)
        assert result["status"] == "scored"
        assert result["weight_coverage"] == pytest.approx(1.0)
        assert result["renormalized"] is False
        assert result["breakdown"]["formula"] == "ATS = 0.40K + 0.25E + 0.15D + 0.10P + 0.10M"
        assert result["confidence"] == "high"

    def test_missing_component_is_excluded_and_weights_renormalised(self):
        weights = ats_service.get_weights()
        returns = [
            component("skills", weights["skills"], 80),
            component(
                "experience",
                weights["experience"],
                None,
                status="insufficient_data",
                missing=["No experience information."],
            ),
            component("education", weights["education"], 60),
            component("projects", weights["projects"], 40),
            component("semantic", weights["semantic"], 50, dq="model_generated"),
        ]
        with patch(ALL_COMPONENT_PATCHES[0], return_value=returns[0]), \
             patch(ALL_COMPONENT_PATCHES[1], return_value=returns[1]), \
             patch(ALL_COMPONENT_PATCHES[2], return_value=returns[2]), \
             patch(ALL_COMPONENT_PATCHES[3], return_value=returns[3]), \
             patch(ALL_COMPONENT_PATCHES[4], return_value=returns[4]):
            result = ats_service.compute_ats_score(make_resume(), make_job())

        # Available weights: .40 + .15 + .10 + .10 = .75
        # (32 + 9 + 4 + 5) / .75 = 66.67
        assert result["ats_score"] == pytest.approx(66.67, abs=0.01)
        assert result["weight_coverage"] == pytest.approx(0.75)
        assert result["renormalized"] is True
        assert result["status"] == "partial"
        assert result["breakdown"]["component_scores"]["experience"] is None
        assert result["breakdown"]["effective_weights"]["experience"] == 0.0
        assert result["breakdown"]["effective_weights"]["skills"] == pytest.approx(0.533333, abs=0.001)
        assert any(
            item["component"] == "experience"
            for item in result["breakdown"]["missing_information"]
        )

    def test_all_components_missing_returns_no_score(self):
        weights = ats_service.get_weights()
        returns = [
            component("skills", weights["skills"], None, "insufficient_data", ["missing"]),
            component("experience", weights["experience"], None, "insufficient_data", ["missing"]),
            component("education", weights["education"], None, "insufficient_data", ["missing"]),
            component("projects", weights["projects"], None, "insufficient_data", ["missing"]),
            component("semantic", weights["semantic"], None, "insufficient_data", ["missing"], "model_generated"),
        ]
        with patch(ALL_COMPONENT_PATCHES[0], return_value=returns[0]), \
             patch(ALL_COMPONENT_PATCHES[1], return_value=returns[1]), \
             patch(ALL_COMPONENT_PATCHES[2], return_value=returns[2]), \
             patch(ALL_COMPONENT_PATCHES[3], return_value=returns[3]), \
             patch(ALL_COMPONENT_PATCHES[4], return_value=returns[4]):
            result = ats_service.compute_ats_score(make_resume(), make_job())

        assert result["ats_score"] is None
        assert result["status"] == "insufficient_data"
        assert result["confidence"] == "none"
        assert result["weight_coverage"] == 0.0
        assert all(value == 0.0 for value in result["breakdown"]["effective_weights"].values())

    def test_explanation_contains_limitations_and_no_auto_rejection(self):
        weights = ats_service.get_weights()
        returns = [
            component("skills", weights["skills"], 80),
            component("experience", weights["experience"], 60),
            component("education", weights["education"], 70),
            component("projects", weights["projects"], 50),
            component("semantic", weights["semantic"], 90, dq="model_generated"),
        ]
        with patch(ALL_COMPONENT_PATCHES[0], return_value=returns[0]), \
             patch(ALL_COMPONENT_PATCHES[1], return_value=returns[1]), \
             patch(ALL_COMPONENT_PATCHES[2], return_value=returns[2]), \
             patch(ALL_COMPONENT_PATCHES[3], return_value=returns[3]), \
             patch(ALL_COMPONENT_PATCHES[4], return_value=returns[4]):
            result = ats_service.compute_ats_score(make_resume(), make_job())

        breakdown = result["breakdown"]
        assert "does not automatically reject" in breakdown["disclaimer"]
        assert len(breakdown["limitations"]) >= 5
        assert breakdown["computed_at"]
        assert breakdown["scoring_version"] == "ats-v1.0"
        assert len(breakdown["components"]) == 5


# --------------------------------------------------------------------------- #
# Skills                                                                       #
# --------------------------------------------------------------------------- #
class TestSkillComponent:
    def test_required_skill_coverage_and_evidence(self):
        resume = make_resume(
            skills=["Python", "FastAPI", "MySQL"],
            raw_text="Built APIs with Python and FastAPI.",
        )
        job = make_job(required=["Python", "FastAPI", "Docker"], preferred=["AWS"])

        result = ats_service.score_skill_component(resume, job, 0.40)

        assert result["score"] == pytest.approx(66.67, abs=0.01)
        assert result["status"] == "scored"
        assert set(result["details"]["matched_required"]) == {"Python", "FastAPI"}
        assert result["details"]["missing_required"] == ["Docker"]
        evidence_skills = {item["skill"] for item in result["evidence"]}
        assert {"Python", "FastAPI"}.issubset(evidence_skills)

    def test_missing_skills_is_unknown_not_zero(self):
        result = ats_service.score_skill_component(
            make_resume(skills=[]),
            make_job(required=["Python"]),
            0.40,
        )
        assert result["score"] is None
        assert result["status"] == "insufficient_data"
        assert result["missing_information"]
        assert result["weighted_contribution"] == 0.0

    def test_no_job_skills_is_not_applicable(self):
        result = ats_service.score_skill_component(
            make_resume(skills=["Python"]),
            make_job(required=[], preferred=[]),
            0.40,
        )
        assert result["score"] is None
        assert result["status"] == "not_applicable"

    def test_corrected_skills_are_used_when_reviewed(self):
        resume = make_resume(
            skills=["Python"],
            reviewed=True,
            corrected={"skills": ["Python", "FastAPI", "Docker"]},
        )
        result = ats_service.score_skill_component(
            resume,
            make_job(required=["Python", "FastAPI", "Docker"]),
            0.40,
        )
        assert result["score"] == pytest.approx(100.0)
        assert result["data_quality"] == "candidate_reviewed"


# --------------------------------------------------------------------------- #
# Experience                                                                   #
# --------------------------------------------------------------------------- #
class TestExperienceComponent:
    @patch("app.services.ats_service.compute_tfidf_similarity", return_value=1.0)
    def test_years_and_role_relevance(self, _mock_tfidf):
        resume = make_resume(
            experience={"estimated_years": 2.0, "identified_roles": ["Python Developer"]},
            raw_text="2 years of experience as a Python Developer.",
        )
        job = make_job(min_years=4.0)

        result = ats_service.score_experience_component(resume, job, 0.25)

        # 0.70 * 50 + 0.30 * 100 = 65
        assert result["score"] == pytest.approx(65.0)
        assert result["status"] == "scored"
        assert result["details"]["years_ratio"] == pytest.approx(0.5)
        assert result["evidence"]

    @patch("app.services.ats_service.compute_tfidf_similarity", return_value=1.0)
    def test_missing_years_uses_roles_not_zero(self, _mock_tfidf):
        resume = make_resume(
            experience={"estimated_years": None, "identified_roles": ["Backend Developer"]},
            raw_text="Worked as a Backend Developer.",
        )
        result = ats_service.score_experience_component(resume, make_job(min_years=2.0), 0.25)

        assert result["score"] == pytest.approx(100.0)
        assert result["status"] == "partial"
        assert result["missing_information"]
        assert result["score"] is not None

    def test_no_experience_requirement_is_not_applicable(self):
        result = ats_service.score_experience_component(
            make_resume(experience={"estimated_years": 5.0, "identified_roles": ["Engineer"]}),
            make_job(min_years=0.0),
            0.25,
        )
        assert result["score"] is None
        assert result["status"] == "not_applicable"

    def test_no_years_and_no_roles_is_insufficient(self):
        result = ats_service.score_experience_component(
            make_resume(experience={}),
            make_job(min_years=2.0),
            0.25,
        )
        assert result["score"] is None
        assert result["status"] == "insufficient_data"
        assert len(result["missing_information"]) == 2


# --------------------------------------------------------------------------- #
# Education                                                                    #
# --------------------------------------------------------------------------- #
class TestEducationComponent:
    def test_meets_required_level_and_field(self):
        resume = make_resume(
            education=[
                {
                    "degree": "B.Tech in Computer Science",
                    "institution_context": "ABC Institute of Technology, 2024",
                    "year": "2024",
                    "grade_or_cgpa": "8.8",
                }
            ]
        )
        result = ats_service.score_education_component(
            resume,
            make_job(education="Bachelor's Degree in Computer Science"),
            0.15,
        )
        assert result["score"] == pytest.approx(100.0)
        assert result["status"] == "scored"
        assert result["details"]["level_gap"] == 0
        assert result["evidence"]

    def test_one_level_below_is_partial_credit_not_zero(self):
        resume = make_resume(
            education=[{"degree": "B.Tech in Computer Science", "institution_context": "ABC Institute"}]
        )
        result = ats_service.score_education_component(
            resume,
            make_job(education="Master's Degree in Computer Science"),
            0.15,
        )
        # 0.80*60 + 0.20*100 = 68
        assert result["score"] == pytest.approx(68.0)
        assert result["details"]["level_gap"] == -1

    def test_no_education_records_is_unknown_not_zero(self):
        result = ats_service.score_education_component(
            make_resume(education=[]),
            make_job(education="Bachelor's Degree"),
            0.15,
        )
        assert result["score"] is None
        assert result["status"] == "insufficient_data"

    def test_unparsed_degree_is_unknown_not_zero(self):
        result = ats_service.score_education_component(
            make_resume(education=[{"degree": "Higher Education", "institution_context": "Some College"}]),
            make_job(education="Bachelor's Degree"),
            0.15,
        )
        assert result["score"] is None
        assert result["status"] == "insufficient_data"
        assert "parsing limitation" in result["rationale"]


# --------------------------------------------------------------------------- #
# Projects                                                                     #
# --------------------------------------------------------------------------- #
class TestProjectComponent:
    @patch("app.services.ats_service.compute_tfidf_similarity", return_value=0.5)
    def test_skill_coverage_and_text_similarity(self, _mock_tfidf):
        resume = make_resume(
            projects=[
                {
                    "title": "Resume Matcher",
                    "description": "Built with Python and FastAPI.",
                }
            ]
        )
        job = make_job(required=["Python", "FastAPI", "Docker"])
        result = ats_service.score_project_component(resume, job, 0.10)

        # coverage 2/3 = 66.67; 0.70*66.67 + 0.30*50 = 61.67
        assert result["score"] == pytest.approx(61.67, abs=0.01)
        assert result["status"] == "scored"
        assert set(result["details"]["matched_required_skills"]) == {"Python", "FastAPI"}
        assert result["evidence"][0]["title"] == "Resume Matcher"

    def test_no_projects_is_unknown_not_zero(self):
        result = ats_service.score_project_component(
            make_resume(projects=[]),
            make_job(),
            0.10,
        )
        assert result["score"] is None
        assert result["status"] == "insufficient_data"

    @patch("app.services.ats_service.compute_tfidf_similarity", return_value=0.4)
    def test_no_required_skills_uses_text_similarity_only(self, _mock_tfidf):
        result = ats_service.score_project_component(
            make_resume(projects=[{"title": "Portfolio", "description": "A web project."}]),
            make_job(required=[], preferred=[]),
            0.10,
        )
        assert result["score"] == pytest.approx(40.0)
        assert result["status"] == "partial"


# --------------------------------------------------------------------------- #
# Semantic                                                                     #
# --------------------------------------------------------------------------- #
class TestSemanticComponent:
    @patch("app.services.ats_service.compute_semantic_similarity_optional", return_value=0.87)
    def test_semantic_score_scaled_to_100(self, _mock_semantic):
        result = ats_service.score_semantic_component(make_resume(), make_job(), 0.10)
        assert result["score"] == pytest.approx(87.0)
        assert result["status"] == "scored"
        assert result["data_quality"] == "model_generated"

    @patch("app.services.ats_service.compute_semantic_similarity_optional", return_value=None)
    def test_semantic_unavailable_is_unknown_not_zero(self, _mock_semantic):
        result = ats_service.score_semantic_component(make_resume(), make_job(), 0.10)
        assert result["score"] is None
        assert result["status"] == "insufficient_data"
        assert result["missing_information"]

    def test_empty_resume_text_is_insufficient(self):
        result = ats_service.score_semantic_component(
            make_resume(raw_text="   "),
            make_job(),
            0.10,
        )
        assert result["score"] is None
        assert result["status"] == "insufficient_data"


# --------------------------------------------------------------------------- #
# Ranking                                                                      #
# --------------------------------------------------------------------------- #
class TestRanking:
    def test_ranking_orders_by_score_then_skill_then_candidate_id(self):
        items = [
            {"candidate_id": 3, "ats_score": 70.0, "component_scores": {"skills": 80.0}},
            {"candidate_id": 1, "ats_score": 90.0, "component_scores": {"skills": 70.0}},
            {"candidate_id": 2, "ats_score": 70.0, "component_scores": {"skills": 90.0}},
            {"candidate_id": 4, "ats_score": None, "component_scores": {}},
        ]

        ranked = ats_service.rank_candidates(items)

        assert [item["candidate_id"] for item in ranked] == [1, 2, 3, 4]
        assert [item["rank"] for item in ranked] == [1, 2, 3, None]

    def test_unscored_candidates_are_last_and_never_ranked_low(self):
        items = [
            {"candidate_id": 1, "ats_score": None, "component_scores": {}},
            {"candidate_id": 2, "ats_score": 10.0, "component_scores": {"skills": 10.0}},
        ]
        ranked = ats_service.rank_candidates(items)
        assert ranked[0]["candidate_id"] == 2
        assert ranked[0]["rank"] == 1
        assert ranked[1]["rank"] is None

    def test_empty_ranking(self):
        assert ats_service.rank_candidates([]) == []


# --------------------------------------------------------------------------- #
# Configuration and fairness                                                   #
# --------------------------------------------------------------------------- #
class TestConfigurationAndFairness:
    def test_default_weights_sum_to_one(self):
        weights = ats_service.get_weights()
        assert sum(weights.values()) == pytest.approx(1.0)
        assert weights == {
            "skills": 0.40,
            "experience": 0.25,
            "education": 0.15,
            "projects": 0.10,
            "semantic": 0.10,
        }

    def test_invalid_weight_configuration_is_rejected(self):
        from app.core.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                ATS_WEIGHT_SKILL=0.50,
                ATS_WEIGHT_EXPERIENCE=0.25,
                ATS_WEIGHT_EDUCATION=0.15,
                ATS_WEIGHT_PROJECT=0.10,
                ATS_WEIGHT_SEMANTIC=0.10,
            )

    def test_sanitizer_removes_obvious_identifiers_and_protected_lines(self):
        text = (
            "John Doe\n"
            "Gender: Male\n"
            "Email: john@example.com\n"
            "Phone: +91 98765 43210\n"
            "Python developer with FastAPI experience."
        )
        cleaned = ats_service.sanitize_text_for_scoring(text)
        assert "Gender" not in cleaned
        assert "john@example.com" not in cleaned
        assert "98765" not in cleaned
        assert "Python developer" in cleaned

    def test_public_weights_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).get("/api/v1/ats/weights")
        assert response.status_code == 200
        data = response.json()
        assert data["weights"]["skills"] == 0.40
        assert "ATS = 0.40K" in data["formula"]
        assert "not automatically reject" in data["disclaimer"]
