import unittest

from core.extract import Line
from core.parser import parse


class ParserTests(unittest.TestCase):
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
