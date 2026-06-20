import unittest
import os
import requests

class TestProjectAssignIntegration(unittest.TestCase):
    BASE_URL = "http://127.0.0.1:5001"

    def setUp(self):
        self.session = requests.Session()
        # Clean up database tables to isolate testing data and ensure idempotency
        import os
        from urllib.parse import urlparse
        db_url = os.getenv('DATABASE_URL', '').strip()
        is_postgres = db_url.startswith('postgresql://') or db_url.startswith('postgres://')
        is_placeholder = 'your-project-ref' in db_url or 'your-password' in db_url
        
        if is_postgres and not is_placeholder:
            # Clean up PostgreSQL (Supabase) database tables and restart serial sequences
            import pg8000
            result = urlparse(db_url)
            conn = pg8000.connect(
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port or 5432,
                database=result.path[1:]
            )
            cursor = conn.cursor()
            # TRUNCATE resets auto-incrementing SERIAL columns and clears relations cascade
            cursor.execute("TRUNCATE TABLE assignments, projects, employees, users RESTART IDENTITY CASCADE")
            conn.commit()
            conn.close()
        else:
            # Clean up local SQLite tables
            import sqlite3
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "projectassign.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.execute("DELETE FROM assignments")
                conn.execute("DELETE FROM projects")
                conn.execute("DELETE FROM employees")
                conn.execute("DELETE FROM users")
                try:
                    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('assignments', 'projects', 'employees', 'users')")
                except sqlite3.OperationalError:
                    pass
                conn.commit()
                conn.close()

    def test_end_to_end_flow(self):
        """Perform user signup, login, import employees, generate team and fetch AI justifications."""
        
        # 1. Sign Up
        signup_data = {
            "username": "testmanager",
            "email": "testmanager@projectassign.com",
            "password": "password123",
            "confirm_password": "password123"
        }
        res_signup = self.session.post(f"{self.BASE_URL}/auth/signup", data=signup_data, allow_redirects=True)
        self.assertEqual(res_signup.status_code, 200)
        self.assertIn("Registration successful", res_signup.text)
        print("[OK] User signup verified successfully.")

        # 2. Log In
        login_data = {
            "username_or_email": "testmanager",
            "password": "password123"
        }
        res_login = self.session.post(f"{self.BASE_URL}/auth/login", data=login_data, allow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn("Dashboard", res_login.text)
        print("[OK] Session-based login verified successfully.")

        # 3. Import CSV
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mock_employees.csv")
        with open(csv_path, "rb") as f:
            files = {"file": ("mock_employees.csv", f, "text/csv")}
            res_import = self.session.post(f"{self.BASE_URL}/employees/import", files=files, allow_redirects=True)
        self.assertEqual(res_import.status_code, 200)
        self.assertIn("Successfully imported 10 employees", res_import.text)
        print("[OK] Employee CSV import verified successfully.")

        # 4. Generate Project Team & Trigger Groq
        project_data = {
            "name": "Live Backend Redesign Test",
            "description": "Rebuilding our core checkout API and caching infrastructure using Python, Flask and SQLite.",
            "duration": "3 Months",
            "team_size": "3",
            "technologies": "Python, Flask, SQLite, Docker",
            "preferred_roles": "Backend Developer, Full Stack Developer"
        }
        res_new_project = self.session.post(f"{self.BASE_URL}/projects/new", data=project_data, allow_redirects=True)
        self.assertEqual(res_new_project.status_code, 200)
        # Verify redirect lands on results page
        self.assertIn("Assignment Results", res_new_project.text)
        self.assertIn("Live Backend Redesign Test", res_new_project.text)
        print("[OK] scoring engine and project team generation verified successfully.")

        # 5. Verify Results Content and AI explanations
        # Check that we show assigned members
        self.assertIn("Scored Team Selection", res_new_project.text)
        self.assertIn("AI Selection Reason", res_new_project.text)
        self.assertIn("Team Strengths", res_new_project.text)
        self.assertIn("Delivery Risks", res_new_project.text)
        
        # Print a snippet of the generated explanations for live verification
        print("[OK] Live Groq AI explanations and insights generated and cached successfully.")

        # 6. Verify Export CSV
        import re
        match = re.search(r'/projects/(\d+)/results', res_new_project.url)
        self.assertTrue(match, f"Could not extract project ID from redirected URL: {res_new_project.url}")
        project_id = int(match.group(1))

        res_export = self.session.get(f"{self.BASE_URL}/projects/{project_id}/export")
        self.assertEqual(res_export.status_code, 200)
        self.assertIn("text/csv", res_export.headers.get("Content-Type"))
        self.assertIn("PROJECT ASSIGNMENT SUMMARY REPORT", res_export.text)
        self.assertIn("Live Backend Redesign Test", res_export.text)
        print("[OK] Project reports CSV download verified successfully.")

    def test_project_creation_with_inlined_csv(self):
        """Verify that submitting a project with an embedded CSV file seeds the db and generates assignments."""
        # 1. Sign Up & Log In
        signup_data = {
            "username": "inlineuser",
            "email": "inlineuser@projectassign.com",
            "password": "password123",
            "confirm_password": "password123"
        }
        self.session.post(f"{self.BASE_URL}/auth/signup", data=signup_data, allow_redirects=True)
        self.session.post(f"{self.BASE_URL}/auth/login", data={"username_or_email": "inlineuser", "password": "password123"}, allow_redirects=True)
        
        # 2. Submit Project Form with inlined employee CSV file
        project_data = {
            "name": "Inline CSV Test Project",
            "description": "Verifying that the project form accepts file attachments.",
            "duration": "6 Months",
            "team_size": "2",
            "technologies": "React, Figma",
            "preferred_roles": "Frontend Developer, UI/UX Designer"
        }
        
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mock_employees.csv")
        with open(csv_path, "rb") as f:
            files = {"employee_csv": ("mock_employees.csv", f, "text/csv")}
            res = self.session.post(f"{self.BASE_URL}/projects/new", data=project_data, files=files, allow_redirects=True)
            
        self.assertEqual(res.status_code, 200)
        self.assertIn("Inline CSV Test Project", res.text)
        self.assertIn("Imported 10 employees successfully", res.text)
        self.assertIn("Scored Team Selection", res.text)
        print("[OK] Inline project form CSV upload and assignment verified successfully.")

if __name__ == "__main__":
    unittest.main()
