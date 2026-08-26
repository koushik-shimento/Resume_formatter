import unittest

from core.extract import Line
from core.parser import parse


class ParserTests(unittest.TestCase):
    def test_compact_pdf_roles_keep_company_title_wrapping_and_languages(self):
        lines = [
            Line("RADING RICHARD KANGBA", bold=True, size=17),
            Line("PROFESSIONAL SUMMARY", bold=True, size=10),
            Line("Experienced engineer."),
            Line("PROFESSIONAL EXPERIENCE", bold=True, size=10),
            Line("AI Developer | LinkedERP Jun 2026 - Present"),
            Line("AI-Powered ERP Advisory Platform: Building a product", is_bullet=True),
            Line("that recommends an ERP platform."),
            Line("Software Engineer | Societe Generale Jun 2021 - Jun 2026"),
            Line("Microservices & API Engineering", bold=True, size=9),
            Line("Architected Spring Boot services", is_bullet=True),
            Line("under high concurrency."),
            Line("LANGUAGES", bold=True, size=10),
            Line("English (Fluent) • Hindi (Fluent)"),
        ]
        data = parse(lines)
        self.assertEqual((data.experience[0].title, data.experience[0].company), ("AI Developer", "LinkedERP"))
        self.assertEqual(data.experience[0].bullets, ["AI-Powered ERP Advisory Platform: Building a product that recommends an ERP platform."])
        self.assertEqual((data.experience[1].title, data.experience[1].company), ("Software Engineer", "Societe Generale"))
        self.assertEqual(data.experience[1].bullets, ["Microservices & API Engineering: Architected Spring Boot services under high concurrency."])
        self.assertEqual(data.additional_sections[0].title, "LANGUAGES")

    def test_ocr_header_discards_logo_text(self):
        data = parse([Line("Asit Kumar Mandal SHIM=NTO X"), Line("SUMMARY", bold=True), Line("Experienced architect", is_bullet=True)])
        self.assertEqual(data.name, "Asit Kumar Mandal")

    def test_parses_branded_project_card_resume(self):
        lines = [
            Line("ASIT KUMAR MANDAL", bold=True, size=23),
            Line("⚡ PROFESSIONAL SUMMARY — AI ARCHITECT PROFILE", bold=True, size=11),
            Line("Enterprise architect", is_bullet=True),
            Line("🧠 CORE AI CAPABILITIES & TECHNICAL SKILLS", bold=True, size=11),
            Line("Cloud Platforms: AWS, Azure"),
            Line("💼 FEATURED PROJECTS — AI-ENABLED ARCHITECTURE", bold=True, size=11),
            Line("PROJECT 1 ▸ Verizon OSS Modernization", bold=True, size=11),
            Line("Client: Verizon (Infinite Computer Solutions) Role: Senior Solution Architect  Period: Jul 2025 – Present"),
            Line("Tech Stack: AWS · LangChain"),
            Line("Built the modernization platform", is_bullet=True),
            Line("📊 EARLIER CAREER", bold=True, size=11),
            Line("Team Lead — E2E Provisioning | Tech Mahindra", bold=True),
            Line("Feb 2012 – Apr 2015"),
            Line("Activation System Design"),
            Line("🎓 EDUCATION & CERTIFICATIONS", bold=True, size=11),
            Line("🎓 Education", bold=True),
            Line("MCA — Utkal University, Orissa", is_bullet=True),
            Line("🏆 Certifications & Training", bold=True),
            Line("AWS Certified Solution Architect", is_bullet=True),
        ]

        data = parse(lines)

        self.assertEqual(data.summary, ["Enterprise architect"])
        self.assertEqual(data.skills[0].category, "Cloud Platforms")
        self.assertEqual(len(data.experience), 2)
        self.assertEqual(data.experience[0].company, "Infinite Computer Solutions")
        self.assertEqual(data.experience[0].title, "Senior Solution Architect")
        self.assertIn("AWS · LangChain", data.experience[0].project)
        self.assertEqual(data.experience[1].company, "Tech Mahindra")
        self.assertTrue(data.education)
        self.assertEqual(data.certifications, ["AWS Certified Solution Architect"])

    def test_splits_two_column_inline_section_headings(self):
        lines = [
            Line("Asit Kumar Mandal", bold=True, size=18),
            Line("Professional Summary | Cloud engineer with AWS experience"),
            Line("Technical Skills | Cloud: AWS, Bedrock"),
            Line("Professional Experience | Example Ltd  Jan 2022 - Present"),
            Line("Cloud Engineer"),
            Line("Built reliable services", is_bullet=True),
            Line("Education"),
            Line("MCA | Utkal University | 2020"),
            Line("B.Sc | Rajendra College | 2017 | 🏆 Certifications & Training |"),
            Line("AWS Certified Solutions Architect - Associate"),
        ]

        data = parse(lines)

        self.assertEqual(data.name, "Asit Kumar Mandal")
        self.assertIn("Cloud engineer with AWS experience", data.summary)
        self.assertEqual(data.skills[0].category, "Cloud")
        self.assertEqual(data.experience[0].company, "Example Ltd")
        self.assertTrue(data.education)
        self.assertEqual(
            data.certifications,
            ["AWS Certified Solutions Architect - Associate"],
        )

    def test_parses_expected_resume_sections(self):
        lines = [
            Line("Koushik Kolla", bold=True, size=18),
            Line("Summary"),
            Line("Python developer", is_bullet=True),
            Line("Technical Skills"),
            Line("Languages: Python, SQL"),
            Line("Professional Experience"),
            Line("Shimento  Jan 2024 - Present"),
            Line("Software Engineer"),
            Line("Built resume automation", is_bullet=True),
            Line("Education"),
            Line("B.Tech, Example University, 2023"),
        ]

        data = parse(lines)

        self.assertEqual(data.name, "Koushik Kolla")
        self.assertEqual(data.summary, ["Python developer"])
        self.assertEqual(data.skills[0].category, "Languages")
        self.assertEqual(data.experience[0].company, "Shimento")
        self.assertEqual(data.experience[0].title, "Software Engineer")
        self.assertEqual(data.education[0].year, "2023")

    def test_uses_filename_when_name_is_missing(self):
        data = parse([Line("Summary"), Line("Experienced engineer", is_bullet=True)],
                     fallback_name="Jane Doe")
        self.assertEqual(data.name, "Jane Doe")

    def test_repeated_parse_keeps_every_summary_and_skill_entry(self):
        for iteration in range(1, 21):
            summaries = [f"Summary {iteration}-{index}" for index in range(1, 6)]
            skills = [(f"Category {index}", f"Skill {iteration}-{index}")
                      for index in range(1, 5)]
            lines = [Line(f"Candidate {iteration}"), Line("Summary")]
            lines.extend(Line(value, is_bullet=True) for value in summaries)
            lines.append(Line("Technical Skills"))
            lines.extend(Line(f"{category}: {value}") for category, value in skills)

            data = parse(lines)

            self.assertEqual(data.summary, summaries, f"summary loss in iteration {iteration}")
            self.assertEqual(
                [(group.category, group.values) for group in data.skills],
                skills,
                f"skill loss in iteration {iteration}",
            )


if __name__ == "__main__":
    unittest.main()
