import unittest
from app.projects.engine import parse_availability, score_employee, rank_employees_for_project

class TestScoringEngine(unittest.TestCase):
    
    def test_parse_availability_text(self):
        """Test text indicators of availability."""
        self.assertEqual(parse_availability("Available"), 100.0)
        self.assertEqual(parse_availability("active"), 100.0)
        self.assertEqual(parse_availability("yes"), 100.0)
        self.assertEqual(parse_availability("Unavailable"), 0.0)
        self.assertEqual(parse_availability("no"), 0.0)
        self.assertEqual(parse_availability("false"), 0.0)
        
    def test_parse_availability_percentages(self):
        """Test percentage signs and decimal indicators of availability."""
        self.assertEqual(parse_availability("80%"), 80.0)
        self.assertEqual(parse_availability("0.75"), 75.0)
        self.assertEqual(parse_availability("50"), 50.0)
        self.assertEqual(parse_availability("1.0"), 100.0)
        self.assertEqual(parse_availability("0"), 0.0)
        
    def test_parse_availability_fallbacks(self):
        """Test fallback states for invalid formats."""
        self.assertEqual(parse_availability(""), 100.0)
        self.assertEqual(parse_availability(None), 100.0)
        self.assertEqual(parse_availability("Unknown Text"), 100.0)

    def test_score_employee_perfect(self):
        """Test employee with perfect matches on all dimensions."""
        employee = {
            'skills': 'Python, Flask, SQLite, React',
            'role': 'Full Stack Developer',
            'experience': 10,
            'availability': 'Available',
            'performance_score': 100
        }
        project_techs = ['python', 'flask']
        project_roles = ['full stack developer']
        
        scores = score_employee(employee, project_techs, project_roles)
        
        # Breakdown:
        # Skills match: 100% * 0.40 = 40
        # Role match: 100% * 0.25 = 25
        # Perf match: 100% * 0.20 = 20
        # Exp match: 10/10=100% * 0.10 = 10
        # Avail match: 100% * 0.05 = 5
        # Total: 100
        self.assertEqual(scores['skills_score'], 100.0)
        self.assertEqual(scores['role_score'], 100.0)
        self.assertEqual(scores['perf_score'], 100.0)
        self.assertEqual(scores['exp_score'], 100.0)
        self.assertEqual(scores['avail_score'], 100.0)
        self.assertEqual(scores['total_score'], 100.0)

    def test_score_employee_partial(self):
        """Test employee with partial matches on skills, roles, and experience."""
        employee = {
            'skills': 'Python, Docker',
            'role': 'Backend Developer',
            'experience': 5,  # 50% score
            'availability': '80%',  # 80% score
            'performance_score': 90
        }
        # Project requires Python and React (employee matches 1 of 2: 50% skills)
        project_techs = ['python', 'react']
        # Project prefers Frontend Developer (employee has Backend: 0% role)
        project_roles = ['frontend developer']
        
        scores = score_employee(employee, project_techs, project_roles)
        
        # Breakdown:
        # Skills match: 50.0% -> weight 40% -> 20.0
        # Role match: 0.0% -> weight 25% -> 0.0
        # Perf match: 90.0% -> weight 20% -> 18.0
        # Exp match: 50.0% (5 yrs / 10) -> weight 10% -> 5.0
        # Avail match: 80.0% -> weight 5% -> 4.0
        # Total: 20 + 0 + 18 + 5 + 4 = 47.0
        self.assertEqual(scores['skills_score'], 50.0)
        self.assertEqual(scores['role_score'], 0.0)
        self.assertEqual(scores['perf_score'], 90.0)
        self.assertEqual(scores['exp_score'], 50.0)
        self.assertEqual(scores['avail_score'], 80.0)
        self.assertEqual(scores['total_score'], 47.0)

    def test_rank_employees(self):
        """Test sorting candidates by final score descending."""
        employees = [
            {'employee_id': 'E1', 'name': 'Alice', 'skills': 'Python', 'role': 'Dev', 'experience': 5, 'availability': 'Yes', 'performance_score': 70},
            {'employee_id': 'E2', 'name': 'Bob', 'skills': 'Python, React', 'role': 'Dev', 'experience': 10, 'availability': 'Yes', 'performance_score': 95},
            {'employee_id': 'E3', 'name': 'Charlie', 'skills': 'Java', 'role': 'QA', 'experience': 2, 'availability': 'No', 'performance_score': 60}
        ]
        project = {
            'technologies': 'Python, React',
            'preferred_roles': 'Dev'
        }
        
        ranked = rank_employees_for_project(employees, project)
        
        self.assertEqual(len(ranked), 3)
        # Bob (E2) must be ranked #1
        self.assertEqual(ranked[0][0]['employee_id'], 'E2')
        # Charlie (E3) should be last
        self.assertEqual(ranked[2][0]['employee_id'], 'E3')
        
        # Check that scores are ordered descending
        self.assertTrue(ranked[0][1]['total_score'] >= ranked[1][1]['total_score'])
        self.assertTrue(ranked[1][1]['total_score'] >= ranked[2][1]['total_score'])

if __name__ == '__main__':
    unittest.main()
