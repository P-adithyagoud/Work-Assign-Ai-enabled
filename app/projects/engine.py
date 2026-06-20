import re

def parse_availability(avail_str):
    """
    Parse employee availability string into a float score between 0.0 and 100.0.
    Handles text indicators, percentage signs, and decimal values.
    """
    if not avail_str:
        return 100.0  # Default fallback if empty
        
    s = str(avail_str).strip().lower()
    
    # Check text indicators
    if s in ('available', 'active', 'yes', 'true', 'full-time', 'fulltime', '1'):
        return 100.0
    if s in ('unavailable', 'inactive', 'no', 'false', 'none', '0'):
        return 0.0
        
    # Check for percentage (e.g., "80%")
    if '%' in s:
        try:
            num = float(s.replace('%', '').strip())
            return max(0.0, min(100.0, num))
        except ValueError:
            pass
            
    # Try parsing directly as float
    try:
        val = float(s)
        # If represented as a decimal fraction (e.g. 0.8 or 1.0)
        if 0.0 <= val <= 1.0:
            return val * 100.0
        # If represented as raw percentage values (e.g. 80.0)
        return max(0.0, min(100.0, val))
    except ValueError:
        pass
        
    # Fallback default
    return 100.0

def score_employee(employee, project_techs, project_roles):
    """
    Calculate compatibility scores for a single employee relative to project needs.
    Returns a dict containing total_score and component breakdown.
    """
    # 1. Skills Match (40%)
    emp_skills = [s.strip().lower() for s in employee['skills'].split(',') if s.strip()]
    if not project_techs:
        skills_score = 100.0
    else:
        matches = set(project_techs).intersection(set(emp_skills))
        skills_score = (len(matches) / len(project_techs)) * 100.0
        
    # 2. Role Match (25%)
    emp_role = employee['role'].strip().lower()
    if not project_roles:
        role_score = 100.0
    else:
        role_score = 100.0 if emp_role in project_roles else 0.0
        
    # 3. Performance Match (20%)
    try:
        perf_score = float(employee['performance_score'])
        perf_score = max(0.0, min(100.0, perf_score))
    except (ValueError, TypeError):
        perf_score = 0.0
        
    # 4. Experience Match (10%)
    try:
        exp_years = float(employee['experience'])
        # Scaled linearly against a 10-year threshold
        exp_score = min(exp_years / 10.0, 1.0) * 100.0
    except (ValueError, TypeError):
        exp_score = 0.0
        
    # 5. Availability Match (5%)
    avail_score = parse_availability(employee['availability'])
    
    # Calculate weighted total score
    total_score = (
        (skills_score * 0.40) +
        (role_score * 0.25) +
        (perf_score * 0.20) +
        (exp_score * 0.10) +
        (avail_score * 0.05)
    )
    
    return {
        'skills_score': skills_score,
        'role_score': role_score,
        'perf_score': perf_score,
        'exp_score': exp_score,
        'avail_score': avail_score,
        'total_score': total_score
    }

def rank_employees_for_project(employees, project):
    """
    Ranks a list of employees for a project configuration.
    Returns a sorted list of tuples (employee, score_breakdown).
    """
    project_techs = [t.strip().lower() for t in project['technologies'].split(',') if t.strip()]
    project_roles = [r.strip().lower() for r in project['preferred_roles'].split(',') if r.strip()]
    
    scored_list = []
    for emp in employees:
        score_breakdown = score_employee(emp, project_techs, project_roles)
        scored_list.append((emp, score_breakdown))
        
    # Sort descending by total score
    scored_list.sort(key=lambda x: x[1]['total_score'], reverse=True)
    return scored_list
