"""Client-neutral resume structure that every parser produces and every
 template renderer consumes."""

from dataclasses import asdict, dataclass, field


@dataclass
class Job:
    company: str = ""
    dates: str = ""
    title: str = ""
    project: str = ""
    bullets: list[str] = field(default_factory=list)


@dataclass
class Education:
    degree: str = ""
    institution: str = ""
    year: str = ""


@dataclass
class SkillGroup:
    category: str = ""
    values: str = ""


@dataclass
class ResumeData:
    """Canonical resume payload shared by parsers, LLM normalization, and renderers."""

    name: str = ""
    summary: list[str] = field(default_factory=list)
    skills: list[SkillGroup] = field(default_factory=list)
    experience: list[Job] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    # Source sections that do not map into the selected output format.
    dropped_sections: list[str] = field(default_factory=list)
    # How the final structure was produced: rule-based, llm, or llm_fallback.
    normalization_method: str = "rule-based"
    # Human-readable note for the review UI; empty when no fallback/error occurred.
    normalization_note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ResumeData":
        """Build a ResumeData instance from trusted/validated JSON-like data."""
        return cls(
            name=str(d.get("name", "")),
            summary=[str(x) for x in d.get("summary", [])],
            skills=[
                SkillGroup(
                    category=str(s.get("category", "")),
                    values=str(s.get("values", "")),
                )
                for s in d.get("skills", [])
            ],
            experience=[
                Job(
                    company=str(j.get("company", "")),
                    dates=str(j.get("dates", "")),
                    title=str(j.get("title", "")),
                    project=str(j.get("project", "")),
                    bullets=[str(x) for x in j.get("bullets", [])],
                )
                for j in d.get("experience", [])
            ],
            certifications=[str(x) for x in d.get("certifications", [])],
            education=[
                Education(
                    degree=str(e.get("degree", "")),
                    institution=str(e.get("institution", "")),
                    year=str(e.get("year", "")),
                )
                for e in d.get("education", [])
            ],
            dropped_sections=[str(x) for x in d.get("dropped_sections", [])],
            normalization_method=str(d.get("normalization_method", "rule-based")),
            normalization_note=str(d.get("normalization_note", "")),
        )
