from flask import Blueprint, jsonify, request, g
from app.auth.routes import login_required
from app.database import get_db

bp = Blueprint('api_projects', __name__, url_prefix='/api/projects')

@bp.route('/', methods=['GET'])
@login_required
def get_projects():
    db = get_db()
    try:
        # Fetch projects along with tasks and assignments count using Supabase embedding
        res = db.table('projects').select('*, tasks(id, status), assignments(id)').eq('created_by', g.user['id']).order('created_at', desc=True).execute()
        raw_projects = res.data
        
        projects = []
        for p in raw_projects:
            p_copy = dict(p)
            tasks = p.get('tasks', [])
            p_copy['open_tasks_count'] = len([t for t in tasks if t['status'] not in ('Completed',)])
            p_copy['completed_tasks'] = len([t for t in tasks if t['status'] == 'Completed'])
            p_copy['total_tasks'] = len(tasks)
            p_copy['completion_percentage'] = int((p_copy['completed_tasks'] / p_copy['total_tasks']) * 100) if p_copy['total_tasks'] > 0 else 0
            
            p_copy['assigned_count'] = len(p.get('assignments', []))
            # Just send necessary data to UI to compute risks
            projects.append(p_copy)
            
        return jsonify({"projects": projects}), 200
    except Exception as e:
        print(f"API Error fetching projects: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:project_id>', methods=['GET'])
@login_required
def get_project_details(project_id):
    db = get_db()
    try:
        res = db.table('projects').select('*').eq('id', project_id).eq('created_by', g.user['id']).execute()
        if not res.data:
            return jsonify({"error": "Project not found"}), 404
            
        project = res.data[0]
        return jsonify({"project": project}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:project_id>/tasks', methods=['GET'])
@login_required
def get_project_tasks(project_id):
    db = get_db()
    try:
        # Get tasks with assignee details
        res = db.table('tasks').select('*, employees(*)').eq('project_id', project_id).execute()
        return jsonify({"tasks": res.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:project_id>/team', methods=['GET'])
@login_required
def get_project_team(project_id):
    db = get_db()
    try:
        # Get assignments joined with employee info
        assign_res = db.table('assignments').select('*, employees(*)').eq('project_id', project_id).execute()
        
        team = []
        for a in assign_res.data:
            emp_data = a.get('employees', {})
            emp_data['assignment_id'] = a['id']
            emp_data['match_score'] = a['match_score']
            emp_data['project_role'] = a['role']
            emp_data['utilization'] = a['utilization']
            team.append(emp_data)
            
        return jsonify({"team": team}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:project_id>/milestones', methods=['GET'])
@login_required
def get_project_milestones(project_id):
    db = get_db()
    try:
        res = db.table('milestones').select('*').eq('project_id', project_id).order('due_date').execute()
        return jsonify({"milestones": res.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
