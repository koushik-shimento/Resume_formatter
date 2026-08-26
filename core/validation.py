"""Fail-safe checks that prevent silently corrupted resume exports."""

from __future__ import annotations

import re
from collections import Counter

from .extract import Line
from .model import ResumeData
from .parser import DATE_RANGE


def validate(data: ResumeData, source_lines: list[Line] | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not data.name.strip():
        errors.append("Candidate name was not detected.")
    if not any((data.summary, data.skills, data.experience, data.education)):
        errors.append("No supported resume sections were detected.")
    for index, job in enumerate(data.experience, 1):
        if "|" in job.company or "|" in job.title:
            errors.append(f"Role {index} still contains an unsplit Title | Company header.")
        if not (job.company or job.project):
            errors.append(f"Role {index} has no company or project name.")
        if not job.title:
            warnings.append(f"Role {index} has no detected job title.")
        seen: set[str] = set()
        for bullet in job.bullets:
            key = re.sub(r"\W+", " ", bullet).strip().lower()
            if key and key in seen:
                errors.append(f"Role {index} contains a duplicate responsibility.")
                break
            seen.add(key)
    if source_lines is not None:
        source_bullets = sum(line.is_bullet for line in source_lines)
        retained_bullets = (
            len(data.summary) + sum(len(job.bullets) for job in data.experience)
            + len(data.certifications)
            + sum(len(section.items) for section in data.additional_sections)
        )
        if source_bullets >= 3 and retained_bullets < source_bullets * 0.85:
            errors.append(
                f"Only {retained_bullets} of at least {source_bullets} source list items "
                "were mapped; review is required before export."
            )
        pipe_headers = sum(
            1 for line in source_lines if "|" in line.text and DATE_RANGE.search(line.text)
        )
        complete_jobs = sum(bool(job.company and job.title) for job in data.experience)
        if pipe_headers and complete_jobs < pipe_headers:
            errors.append(
                f"Detected {pipe_headers} Title | Company headers but only "
                f"{complete_jobs} complete roles."
            )
        if data.normalization_method == "rule-based":
            source_tokens = _source_tokens(source_lines)
            output_tokens = _tokens(_resume_text(data))
            retained = sum((source_tokens & output_tokens).values())
            coverage = retained / sum(source_tokens.values()) if source_tokens else 1.0
            if coverage < 0.70:
                errors.append(
                    f"Only {coverage:.0%} of meaningful source text was retained; "
                    "review is required before export."
                )
            elif coverage < 0.82:
                warnings.append(f"Source-text retention is {coverage:.0%}; review uncommon layout elements.")
    if data.dropped_sections:
        warnings.append("Ignored source sections: " + ", ".join(data.dropped_sections))
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))


def _source_tokens(lines: list[Line]) -> Counter[str]:
    kept = []
    for line in lines:
        low = line.text.lower()
        if "@" in line.text or "linkedin" in low or re.search(r"\d[\d\s()+-]{7,}\d", line.text):
            continue
        kept.append(line.text)
    return _tokens(" ".join(kept))


def _tokens(text: str) -> Counter[str]:
    stop = {"summary", "professional", "experience", "technical", "skills", "education", "responsibilities"}
    return Counter(
        token for token in re.findall(r"[a-z0-9+#.]{3,}", text.lower())
        if token not in stop
    )


def _resume_text(data: ResumeData) -> str:
    parts = [data.name, *data.summary]
    parts.extend(f"{skill.category} {skill.values}" for skill in data.skills)
    for job in data.experience:
        parts.extend((job.company, job.title, job.dates, job.project, *job.bullets))
    parts.extend(data.certifications)
    parts.extend(f"{item.degree} {item.institution} {item.year}" for item in data.education)
    for section in data.additional_sections:
        parts.extend((section.title, *section.items))
    return " ".join(parts)
