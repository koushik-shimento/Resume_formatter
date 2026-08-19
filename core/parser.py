"""Rule-based resume parser.

Deliberately conservative: when a heuristic is unsure it keeps the text and
puts it somewhere visible rather than guessing hard or dropping it, because a
recruiter correcting a misplaced line in the review screen is cheap, whereas
silently losing a candidate's experience is not.
"""

import re

from .extract import Line
from .model import Education, Job, ResumeData, SkillGroup

_SECTION_ALIASES: dict[str, str] = {}


def _register(section: str, *names: str) -> None:
    for n in names:
        _SECTION_ALIASES[n] = section


_register(
    "summary",
    "summary", "professional summary", "career summary", "executive summary",
    "profile", "professional profile", "personal profile", "profile summary",
    "about", "about me", "overview", "objective", "career objective",
    "professional objective", "synopsis", "professional synopsis", "highlights",
    "career highlights", "summary of qualifications", "key qualifications",
    "professional experience summary", "brief summary",
)
_register(
    "skills",
    "skills", "technical skills", "technical skill", "key skills", "core skills",
    "skill set", "skillset", "technical expertise", "technical proficiency",
    "technical proficiencies", "core competencies", "competencies", "technologies",
    "technology stack", "tech stack", "technical summary", "areas of expertise",
    "expertise", "it skills", "computer skills", "technical knowledge", "tools and technologies",
)
_register(
    "experience",
    "experience", "professional experience", "work experience", "employment history",
    "employment", "work history", "career history", "professional background",
    "relevant experience", "industry experience", "professional work experience",
    "experience summary", "work summary", "career experience", "employment details",
)
_register(
    "projects",
    "projects", "project", "key projects", "academic projects", "personal projects",
    "project experience", "project details", "notable projects", "major projects",
)
_register(
    "certifications",
    "certifications", "certification", "certificates", "certificate",
    "licenses", "licenses and certifications", "licences", "courses",
    "certifications and training", "training", "trainings", "professional development",
)
_register(
    "education",
    "education", "educational qualification", "educational qualifications",
    "academic qualification", "academic qualifications", "academics", "academic background",
    "qualification", "qualifications", "educational background", "education details",
)
_register(
    "ignore",
    "achievements", "accomplishments", "awards", "awards and honors", "honors",
    "hobbies", "interests", "hobbies and interests", "extracurricular activities",
    "activities", "languages", "languages known", "personal details",
    "personal information", "declaration", "references", "reference",
    "publications", "patents", "volunteer experience", "strengths",
    "contact", "contact details", "contact information",
)

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_YEAR = r"(?:19|20)\d{2}"
_TOKEN = (
    rf"(?:{_MONTH}[\s,\-]*(?:{_YEAR}|\d{{2}})"
    rf"|\d{{1,2}}\s*[/\-]\s*(?:{_YEAR}|\d{{2}})"
    rf"|{_YEAR})"
)
_END = rf"(?:{_TOKEN}|present|current|till\s*date|to\s*date|todate|now|ongoing|date)"
_SEP = r"\s*(?:[-–—]{1,2}|\bto\b|\bthrough\b|\buntil\b)\s*"
DATE_RANGE = re.compile(rf"(?P<start>{_TOKEN}){_SEP}(?P<end>{_END})", re.I)

_TITLE_WORDS = (
    "engineer", "developer", "programmer", "architect", "analyst", "consultant",
    "manager", "lead", "director", "administrator", "specialist", "designer",
    "scientist", "tester", "intern", "trainee", "associate", "officer",
    "executive", "coordinator", "supervisor", "head of", "president", "founder",
    "devops", "sre", "qa", "sdet", "recruiter", "accountant", "technician",
)
_DEGREE_WORDS = (
    "bachelor", "master", "b.e", "be ", "b.tech", "btech", "m.tech", "mtech",
    "mba", "b.sc", "bsc", "m.sc", "msc", "b.s.", "m.s.", "phd", "ph.d",
    "diploma", "mca", "bca", "b.a", "m.a", "b.com", "m.com", "associate degree",
    "high school", "intermediate", "secondary", "graduate", "post graduate",
)
_PROJECT_PREFIX = re.compile(r"^\s*(project|client|product|engagement)\s*(name)?\s*[:\-–]\s*", re.I)
_ROLE_MARKER = re.compile(
    r"^\s*(responsibilities|key responsibilities|roles?\s*(and|&)?\s*responsibilities|"
    r"duties|description|job description|contributions?)\s*[:\-–]?\s*$",
    re.I,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_NAME_STOPWORDS = (
    "resume", "curriculum", "vitae", "cv", "phone", "mobile", "email", "e-mail",
    "address", "linkedin", "github", "profile", "contact", "@", "http",
)


def _norm_heading(text: str) -> str:
    t = text.strip().strip(":").strip()
    t = re.sub(r"[^a-zA-Z& ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def _heading_of(line: Line) -> str | None:
    if line.is_bullet:
        return None
    text = line.text.strip()
    if len(text.split()) > 6 or len(text) > 60:
        return None
    return _SECTION_ALIASES.get(_norm_heading(text))


def parse(lines: list[Line], fallback_name: str = "") -> ResumeData:
    data = ResumeData()
    blocks: list[tuple[str, str, list[Line]]] = [("_preamble", "", [])]
    for line in lines:
        section = _heading_of(line)
        if section:
            blocks.append((section, line.text.strip().strip(":"), []))
        else:
            blocks[-1][2].append(line)

    merged: dict[str, list[Line]] = {}
    for section, _, body in blocks:
        merged.setdefault(section, []).extend(body)

    data.name = _parse_name(merged.get("_preamble", []), fallback_name)
    data.summary = _parse_summary(merged.get("summary", []))
    data.skills = _parse_skills(merged.get("skills", []))
    data.experience = _parse_experience(merged.get("experience", []))
    data.experience += _parse_projects(merged.get("projects", []))
    data.certifications = _parse_simple_list(merged.get("certifications", []))
    data.education = _parse_education(merged.get("education", []))

    data.dropped_sections = sorted({
        title for section, title, body in blocks if section == "ignore" and body and title
    })

    # A resume with no recognised headings still has content worth showing.
    if not any((data.summary, data.skills, data.experience, data.education)):
        body = merged.get("_preamble", [])
        data.summary = _parse_summary(body[1:] if body else [])

    return data


def _parse_name(preamble: list[Line], fallback: str) -> str:
    best, best_score = "", -1.0
    for idx, line in enumerate(preamble[:8]):
        raw = line.text.strip()
        candidate = re.split(r"[|,/–—]| - ", raw)[0].strip()
        candidate = re.sub(r"^(name|mr|mrs|ms|dr)\.?\s*[:\-]?\s*", "", candidate, flags=re.I).strip()
        low = candidate.lower()
        if not candidate or any(w in low for w in _NAME_STOPWORDS):
            continue
        if any(ch.isdigit() for ch in candidate):
            continue
        words = candidate.split()
        if not 1 <= len(words) <= 5:
            continue
        if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", w) for w in words):
            continue
        if _SECTION_ALIASES.get(_norm_heading(candidate)):
            continue
        score = 10.0 - idx
        if line.bold:
            score += 4
        if line.size:
            score += min(line.size, 30) / 10
        if candidate.isupper() or candidate.istitle():
            score += 2
        if score > best_score:
            best, best_score = candidate, score
    if not best:
        best = fallback
    if best.isupper():
        best = best.title()
    return best


def _paragraphs(lines: list[Line]) -> list[tuple[str, bool]]:
    """Rejoin PDF/Word soft-wrapped lines into paragraphs, keeping bullet state."""
    out: list[tuple[str, bool]] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            out.append((" ".join(buf).strip(), False))
            buf.clear()

    for line in lines:
        if line.is_bullet:
            flush()
            out.append((line.text, True))
        else:
            buf.append(line.text)
    flush()
    return [(t, b) for t, b in out if t]


def _parse_summary(lines: list[Line]) -> list[str]:
    items: list[str] = []
    for text, is_bullet in _paragraphs(lines):
        if is_bullet or len(text) <= 200:
            items.append(text)
        else:
            items.extend(s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip())
    return items


def _parse_skills(lines: list[Line]) -> list[SkillGroup]:
    groups: list[SkillGroup] = []
    for line in lines:
        text = line.text.strip()
        head, sep, tail = text.partition(":")
        if sep and 0 < len(head.split()) <= 5 and not head.strip().endswith("."):
            groups.append(SkillGroup(head.strip(), tail.strip()))
        elif groups:
            joiner = " " if groups[-1].values.endswith(",") else ", "
            groups[-1].values = (groups[-1].values + joiner + text).strip(" ,")
        else:
            groups.append(SkillGroup("", text))
    return [g for g in groups if g.category or g.values]


def _split_header(text: str) -> tuple[str, str]:
    """Pull a date range out of a job header, returning (remainder, dates)."""
    match = DATE_RANGE.search(text)
    if not match:
        return text.strip(), ""
    dates = re.sub(r"\s+", " ", match.group(0)).strip()
    remainder = (text[: match.start()] + " " + text[match.end():]).strip()
    remainder = remainder.strip(" |,-–—\t")
    remainder = re.sub(r"\s{2,}", " ", remainder)
    return remainder, dates


def _looks_like_title(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in _TITLE_WORDS)


def _parse_experience(lines: list[Line]) -> list[Job]:
    if not lines:
        return []

    header_idx = [
        i for i, ln in enumerate(lines)
        if not ln.is_bullet and len(ln.text) < 140 and DATE_RANGE.search(ln.text)
    ]
    if not header_idx:
        # No parseable dates: keep everything as one block so nothing is lost.
        job = Job()
        _fill_job_body(job, lines)
        return [job] if (job.bullets or job.title or job.company) else []

    jobs: list[Job] = []
    for n, start in enumerate(header_idx):
        end = header_idx[n + 1] if n + 1 < len(header_idx) else len(lines)
        job = Job()
        remainder, job.dates = _split_header(lines[start].text)

        # A header holding only dates means the company sits on the line above.
        if not remainder and start > 0:
            prev = lines[start - 1]
            if not prev.is_bullet and (n == 0 or start - 1 > header_idx[n - 1]):
                remainder = prev.text.strip()
        job.company = remainder

        _fill_job_body(job, lines[start + 1: end])

        if not job.title and len(job.company.split()) <= 6 and _looks_like_title(job.company):
            job.title, job.company = job.company, ""
        jobs.append(job)
    return jobs


def _fill_job_body(job: Job, body: list[Line]) -> None:
    pending: list[Line] = []
    for line in body:
        text = line.text.strip()
        if _ROLE_MARKER.match(text):
            continue
        if not line.is_bullet and _PROJECT_PREFIX.match(text) and not job.project:
            job.project = _PROJECT_PREFIX.sub("", text).strip()
            continue
        if (
            not line.is_bullet
            and not job.title
            and not job.bullets
            and len(text.split()) <= 8
            and _looks_like_title(text)
        ):
            job.title = text
            continue
        if line.is_bullet:
            job.bullets.append(text)
        else:
            pending.append(line)

    # Leftover prose becomes bullets; short stray lines are joined to the previous
    # one because they are almost always PDF line-wrap fragments.
    for text, _ in _paragraphs(pending):
        if job.bullets and len(text) < 40 and not text.endswith("."):
            job.bullets[-1] = f"{job.bullets[-1]} {text}".strip()
        elif len(text) > 200:
            job.bullets.extend(s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip())
        else:
            job.bullets.append(text)


def _parse_projects(lines: list[Line]) -> list[Job]:
    if not lines:
        return []
    jobs: list[Job] = []
    current: Job | None = None
    for line in lines:
        text = line.text.strip()
        if not line.is_bullet and (_PROJECT_PREFIX.match(text) or len(text.split()) <= 8):
            current = Job(project=_PROJECT_PREFIX.sub("", text).strip())
            remainder, current.dates = _split_header(current.project)
            current.project = remainder
            jobs.append(current)
        elif current is not None:
            current.bullets.append(text)
        else:
            current = Job(project="", bullets=[text])
            jobs.append(current)
    return [j for j in jobs if j.project or j.bullets]


def _parse_simple_list(lines: list[Line]) -> list[str]:
    return [text for text, _ in _paragraphs(lines)]


def _parse_education(lines: list[Line]) -> list[Education]:
    entries: list[Education] = []
    for text, _ in _paragraphs(lines):
        year_match = re.search(rf"\b{_YEAR}\b(?:\s*[-–]\s*{_YEAR}\b)?", text)
        year = year_match.group(0) if year_match else ""
        body = (text[: year_match.start()] + " " + text[year_match.end():]) if year_match else text
        body = re.sub(r"\s{2,}", " ", body).strip(" ,|-–—\t")

        low = body.lower()
        has_degree = any(w in low for w in _DEGREE_WORDS)
        parts = [p.strip() for p in re.split(r"\s*[,|]\s*|\s+[-–]\s+", body) if p.strip()]

        if has_degree and parts:
            degree_parts = [p for p in parts if any(w in p.lower() for w in _DEGREE_WORDS)]
            other = [p for p in parts if p not in degree_parts]
            entry = Education(", ".join(degree_parts), ", ".join(other), year)
        elif entries and not entries[-1].institution and not has_degree:
            entries[-1].institution = body
            entries[-1].year = entries[-1].year or year
            continue
        else:
            entry = Education("", body, year)

        if entry.degree or entry.institution or entry.year:
            entries.append(entry)
    return entries
