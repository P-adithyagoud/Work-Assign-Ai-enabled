import unittest
from app.utils.scoring_engine import (
    skills_match_score,
    role_match_score,
    experience_score,
    score_employee,
    generate_assignment,
)

class TestScoringEngine(unittest.TestCase):

    def test_role_match_score(self):
        # Exact match
        self.assertEqual(role_match_score("Frontend Developer", ["Frontend Developer"]), 100)
        # Related match
        self.assertEqual(role_match_score("Frontend Developer", ["UI/UX Designer"]), 50)
        # No match
        self.assertEqual(role_match_score("Frontend Developer", ["Backend Developer"]), 0)
        # Empty requirements
        self.assertEqual(role_match_score("Frontend Developer", []), 100)

    def test_skills_match_score(self):
        # Perfect match
        self.assertEqual(skills_match_score("Python, Flask", ["python", "flask"]), 100)
        # Partial match
        self.assertEqual(skills_match_score("Python", ["python", "react"]), 50)
        # No match
        self.assertEqual(skills_match_score("Java", ["python", "react"]), 0)
        # Empty requirements
        self.assertEqual(skills_match_score("Python", []), 100)

    def test_experience_score(self):
        self.assertEqual(experience_score(5, 10), 50.0)
        self.assertEqual(experience_score(12, 10), 100.0)
        self.assertEqual(experience_score(0, 10), 0.0)

    def test_score_employee(self):
        employee = {
            "employee_id": "E1",
            "name": "Alice",
            "skills": "Python, Flask",
            "experience": 5,
            "role": "Frontend Developer",
            "availability": "Available",
            "performance_score": 90,
        }
        project = {
            "project_name": "Test Project",
            "description": "Building a Flask web app in Python.",
            "technology_preferences": "Python, Flask",
            "preferred_roles": ["Frontend Developer"],
        }
        score = score_employee(employee, project, 10)
        
        # Skills match: 100% * 0.40 = 40.0
        # Role match: 100% * 0.25 = 25.0
        # Performance: 90 * 0.20 = 18.0
        # Experience: 5/10 = 50% * 0.10 = 5.0
        # Availability: 100 * 0.05 = 5.0
        # Total: 40 + 25 + 18 + 5 + 5 = 93.0
        self.assertEqual(score["final_score"], 93.0)

    def test_generate_assignment(self):
        employees = [
            {"employee_id": "E1", "name": "Alice", "skills": "Python", "experience": 5, "role": "Frontend Developer", "availability": "Available", "performance_score": 80},
            {"employee_id": "E2", "name": "Bob", "skills": "Java", "experience": 8, "role": "Backend Developer", "availability": "Available", "performance_score": 90},
        ]
        project = {
            "project_name": "Test Project",
            "technology_preferences": "Java",
            "preferred_roles": ["Backend Developer"],
            "team_size": 1,
        }
        res = generate_assignment(employees, project)
        self.assertEqual(len(res["selected_team"]), 1)
        self.assertEqual(res["selected_team"][0]["employee_id"], "E2")

if __name__ == "__main__":
    unittest.main()
