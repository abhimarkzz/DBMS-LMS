from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    COURSE_NOTES = "course_notes"
    WEB_RESEARCH = "web_research"
    HYBRID = "hybrid"
    # Legacy uppercase aliases
    COURSE_NOTES_UPPER = "COURSE_NOTES"
    WEB_RESEARCH_UPPER = "WEB_RESEARCH"
    HYBRID_UPPER = "HYBRID"

    @classmethod
    def normalize(cls, val: str) -> "SearchMode":
        s = (val or "").strip().lower()
        if s in ("web_research", "web", "web-research"):
            return cls.WEB_RESEARCH
        if s in ("hybrid", "both", "both_sources"):
            return cls.HYBRID
        return cls.COURSE_NOTES


class ResearchDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"
    QUICK_UPPER = "QUICK"
    STANDARD_UPPER = "STANDARD"
    DEEP_UPPER = "DEEP"

    @classmethod
    def normalize(cls, val: str) -> "ResearchDepth":
        s = (val or "").strip().lower()
        if s == "quick":
            return cls.QUICK
        if s == "deep":
            return cls.DEEP
        return cls.STANDARD


class FreshnessPreference(str, Enum):
    ANY = "any"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ANY_UPPER = "ANY"
    DAY_UPPER = "DAY"
    WEEK_UPPER = "WEEK"
    MONTH_UPPER = "MONTH"
    YEAR_UPPER = "YEAR"

    @classmethod
    def normalize(cls, val: str) -> "FreshnessPreference":
        s = (val or "").strip().lower()
        if s in ("day", "24h"):
            return cls.DAY
        if s in ("week", "7d"):
            return cls.WEEK
        if s in ("month", "30d"):
            return cls.MONTH
        if s in ("year", "365d"):
            return cls.YEAR
        return cls.ANY


class NoteUploadRequest(BaseModel):
    course_id: int
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=20)
    material_type: str = "NOTES"


class ChunkResult(BaseModel):
    chunk_id: int
    material_id: int
    material_title: str
    course_id: int
    course_title: str
    chunk_index: int
    chunk_text: str
    similarity_score: float


class WebSourceItem(BaseModel):
    title: str
    url: str
    domain: str
    publication_date: Optional[str] = None  # None or "Unknown", never fabricated
    retrieval_date: str
    snippet: str
    source_type: str = "WEB_GENERAL"  # "OFFICIAL_DOC", "ACADEMIC", "WEB_GENERAL", "GOVERNMENT"
    relevance_score: float = 1.0


class CourseSourceItem(BaseModel):
    chunk_id: int
    material_id: int
    material_title: str
    course_id: int
    course_title: str
    chunk_index: int
    excerpt: str
    similarity_score: float
    download_url: Optional[str] = None


class CitationItem(BaseModel):
    source_id: str
    source_title: str
    source_url: Optional[str] = None
    citation_text: str
    source_type: str = "COURSE_NOTE"  # "COURSE_NOTE" or "WEB"


class AISearchRequest(BaseModel):
    query: str = Field(default="", max_length=1000)
    mode: SearchMode = SearchMode.COURSE_NOTES
    depth: ResearchDepth = ResearchDepth.STANDARD
    freshness: FreshnessPreference = FreshnessPreference.ANY
    course_id: Optional[int] = None
    top_k: int = Field(default=4, ge=1, le=10)


class AISearchResponse(BaseModel):
    query: str
    mode: str = "COURSE_NOTES"
    depth: str = "STANDARD"
    freshness: str = "ANY"
    answer: str
    direct_answer: Optional[str] = None
    key_findings: List[str] = []
    grounded: bool
    sources: List[ChunkResult] = []  # Preserves existing compatibility
    course_sources: List[CourseSourceItem] = []
    web_sources: List[WebSourceItem] = []
    citations: List[CitationItem] = []
    search_status: str = "SUCCESS"  # "SUCCESS", "NO_RESULTS", "PARTIAL_SUCCESS", "QUOTA_EXHAUSTED", "UNAVAILABLE"
    limitations: Optional[str] = None
    model_used: str
    latency_ms: Optional[float] = None
    diagnostics: Optional[Dict[str, Any]] = None
