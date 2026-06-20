from flask import Blueprint, render_template, g
from app.auth.routes import login_required
from app.database import get_db

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/', methods=('GET',))
@login_required
def index():
    """Render the central manager dashboard displaying workforce metrics and summary reports."""
    db = get_db()
    
    # Fetch all projects created by this user
    projects_res = db.table('projects').select('*').eq('created_by', g.user['id']).order('created_at', desc=True).execute()
    user_projects = projects_res.data
    total_projects = len(user_projects)
    project_ids = [p['id'] for p in user_projects]
    
    # Fetch all assignments linked to these projects
    assignments = []
    if project_ids:
        # We need to filter assignments where project_id is in project_ids
        # Since 'in' filter is supported: .in_("project_id", project_ids)
        assignments_res = db.table('assignments').select('*, employees(*), projects(*)').in_('project_id', project_ids).execute()
        assignments = assignments_res.data
        
    active_assignments = len(assignments)
    
    # Average Match Score
    if active_assignments > 0:
        total_score = sum(a['match_score'] for a in assignments)
        avg_project_score = total_score / active_assignments
    else:
        avg_project_score = 0.0
        
    # Total Employees
    all_employees_res = db.table('employees').select('id', count='exact').execute()
    total_employees = all_employees_res.count if all_employees_res.count is not None else len(all_employees_res.data)
    
    # Team Utilization
    assigned_employee_ids = set(a['employee_id'] for a in assignments)
    team_utilization = (len(assigned_employee_ids) / total_employees * 100.0) if total_employees > 0 else 0.0
    
    # Recent Projects (Limit 5)
    recent_projects = []
    for p in user_projects[:5]:
        p_copy = dict(p)
        p_copy['assigned_count'] = sum(1 for a in assignments if a['project_id'] == p['id'])
        recent_projects.append(p_copy)
        
    # Recent Assignments (Limit 5)
    # We want assignments ordered by project's created_at. We can sort them in python.
    sorted_assignments = sorted(assignments, key=lambda x: x['projects']['created_at'] if x.get('projects') else '', reverse=True)
    recent_assignments_list = sorted_assignments[:5]
    
    # Flatten structure for the template
    recent_assignments = []
    for a in recent_assignments_list:
        emp = a.get('employees', {})
        proj = a.get('projects', {})
        recent_assignments.append({
            'employee_name': emp.get('name', 'Unknown'),
            'employee_role': emp.get('role', 'Unknown'),
            'project_name': proj.get('name', 'Unknown'),
            'match_score': a.get('match_score', 0),
            'created_at': proj.get('created_at', '')
        })

    return render_template(
        'dashboard.html',
        total_projects=total_projects,
        active_assignments=active_assignments,
        avg_project_score=avg_project_score,
        team_utilization=team_utilization,
        recent_projects=recent_projects,
        recent_assignments=recent_assignments,
        total_employees=total_employees
    )
