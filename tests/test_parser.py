import unittest

from core.extract import Line
from core.parser import parse


class ParserTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
