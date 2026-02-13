"""
Type definitions for Resume Forge data structures.

This module provides TypedDict definitions for all critical data structures
used throughout the application. These types enable static type checking,
IDE autocomplete, and serve as documentation for data contracts.

TypedDicts are used (instead of dataclasses) because:
- No runtime overhead (static analysis only)
- Compatible with existing dict-based code (no refactor needed)
- Work seamlessly with JSON serialization
- Allow gradual adoption

Phase 1 (Critical): Core data structures for resume/cover letter generation
Phase 2 (Additional): UI and replacement engine structures
"""

from typing import TypedDict, List, Set, Optional, Dict


# ===== PHASE 1: CRITICAL TYPEDDICTS (HIGH PRIORITY) =====

class JDAnalysis(TypedDict):
    """
    Job description intelligence extraction result.

    Extracted by: bullet_intelligence.analyze_job_description()
    Used by: bullet_intelligence.score_bullets_against_jd()
             cover_engine.generate_cover_letter() (Phase 1A optimization)

    Fields:
        required_skills: Must-have skills explicitly required by JD
        preferred_skills: Nice-to-have skills mentioned in JD
        all_keywords: All significant keywords from JD (superset of skills)
        job_categories: Technical categories (frontend, backend, devops, etc.)
    """
    required_skills: List[str]
    preferred_skills: List[str]
    all_keywords: List[str]
    job_categories: List[str]


class AnalyzedBullet(TypedDict, total=False):
    """
    Bullet with extracted intelligence and JD scoring.

    This is a progressive structure - fields are added in stages:

    Stage 1 - Added by analyze_bullets():
        bullet_id: Unique identifier for tracking (format: "bullet_0001")
        text: Raw bullet text content
        keywords: Technical keywords extracted from bullet
        category: Primary technical category (frontend|backend|fullstack|data|devops|cloud|mobile|qa|etc.)
        has_impact: Whether bullet demonstrates measurable impact

    Stage 2 - Added by score_bullets_against_jd():
        jd_score: Relevance score to job description (0.0-10.0+)
        required_matches: JD required skills found in this bullet
        preferred_matches: JD preferred skills found in this bullet

    Note: total=False allows fields to be added progressively
    """
    # Stage 1: Intelligence extraction
    bullet_id: str
    text: str
    keywords: List[str]
    category: str
    has_impact: bool

    # Stage 2: JD scoring
    jd_score: float
    required_matches: List[str]
    preferred_matches: List[str]


class ResumeMetadata(TypedDict):
    """
    Intelligence metadata returned with resume generation result.

    This metadata enables intelligent bullet replacement and tracks
    what intelligence was used during resume generation.

    Fields:
        analyzed_bullets: Full intelligence for all bullets in library
        jd_analysis: Extracted JD intelligence (reused for cover letter)
        used_bullet_ids: Set of bullet IDs that are currently in the resume
    """
    analyzed_bullets: List[AnalyzedBullet]
    jd_analysis: JDAnalysis
    used_bullet_ids: Set[str]


class ResumeData(TypedDict):
    """
    Complete resume generation result.

    Returned by: resume_engine.generate_resume()

    Structure:
        summary: Professional summary paragraph
        spins: List of SPINS bullets (end-user interaction)
        programmer: List of Programmer bullets (technical implementation)
        analyst: List of Analyst bullets (analysis & documentation)
        metadata: Intelligence data for downstream use (replacement, cover letter)
    """
    summary: str
    spins: List[str]
    programmer: List[str]
    analyst: List[str]
    metadata: ResumeMetadata


class Suggestion(TypedDict):
    """
    Single bullet replacement suggestion with scoring.

    Returned by: bullet_intelligence.suggest_replacements()
                 replacement_engine.get_replacement_suggestions()

    Fields:
        bullet: Analyzed bullet with full intelligence
        score: Composite relevance score (higher = better match)
        explanation: Human-readable explanation of why this is suggested
    """
    bullet: AnalyzedBullet
    score: float
    explanation: str


# ===== PHASE 2: ADDITIONAL TYPEDDICTS (MEDIUM PRIORITY) =====

class CompanyInterest(TypedDict, total=False):
    """
    Optional company-specific cover letter content.

    Used by: cover_engine.generate_cover_letter()

    When provided (with at least one non-empty field), adds a
    "motivation/company interest" paragraph to cover letter.

    Fields:
        hook: What caught your attention about the company
        alignment: How their focus aligns with your experience
        credibility_anchor: Specific concrete reference (funding, product, tech)
    """
    hook: str
    alignment: str
    credibility_anchor: str


class ReplacementResult(TypedDict):
    """
    Result from execute_replacement().

    Returned by: replacement_engine.execute_replacement()

    Contains updated section lists (with IDs and text), tracking state,
    and context about what was replaced.

    Fields:
        success: Whether replacement succeeded
        updated_spins: SPINS bullets with IDs (enriched)
        updated_programmer: Programmer bullets with IDs (enriched)
        updated_analyst: Analyst bullets with IDs (enriched)
        updated_used_ids: Updated set of active bullet IDs
        spins_text: Text representation for UI textboxes
        programmer_text: Text representation for UI textboxes
        analyst_text: Text representation for UI textboxes
        replacement_bullet: The new bullet that was inserted
        old_bullet: The bullet that was removed
    """
    success: bool
    updated_spins: List[Dict[str, str]]  # EnrichedBullets
    updated_programmer: List[Dict[str, str]]
    updated_analyst: List[Dict[str, str]]
    updated_used_ids: Set[str]
    spins_text: str
    programmer_text: str
    analyst_text: str
    replacement_bullet: AnalyzedBullet
    old_bullet: Dict[str, str]  # EnrichedBullet


class BulletAssignment(TypedDict):
    """
    Distribution engine bullet assignment.

    Used by: distribution_engine.classify_bullets()

    Represents the LLM's decision about which section a bullet belongs to.

    Fields:
        bullet: Bullet text content
        section: Target section ("spins"|"programmer"|"analyst")
    """
    bullet: str
    section: str  # Literal["spins", "programmer", "analyst"] in Python 3.8+


class EnrichedBullet(TypedDict, total=False):
    """
    UI-layer bullet with tracking ID.

    Created by: ui_formatters.enrich_section_lists_with_ids()

    Minimal structure for UI state management. May optionally include
    analyzed fields if derived from AnalyzedBullet.

    Required fields:
        text: Bullet text content
        bullet_id: Unique identifier for tracking

    Optional fields (if derived from AnalyzedBullet):
        All fields from AnalyzedBullet (keywords, category, jd_score, etc.)
    """
    text: str
    bullet_id: str
    # Optional: may include any AnalyzedBullet fields


class CanonicalBullet(TypedDict, total=False):
    """
    Canonical state representation (Phase 3: State Unification).

    Single source of truth for section bullets. Each bullet tracks
    its section assignment and carries full intelligence.

    Required fields:
        text: Bullet text content
        bullet_id: Unique identifier
        section: Which resume section this bullet belongs to

    Optional fields (intelligence):
        All AnalyzedBullet fields (keywords, category, jd_score, etc.)
    """
    text: str
    bullet_id: str
    section: str  # "spins"|"programmer"|"analyst"
    # Optional: may include any AnalyzedBullet fields
