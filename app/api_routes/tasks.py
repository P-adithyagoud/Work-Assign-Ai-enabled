from flask import Blueprint, jsonify, request, g
from app.auth.routes import login_required
from app.database import get_db

bp = Blueprint('api_tasks', __name__, url_prefix='/api/tasks')

@bp.route('/', methods=['POST'])
@login_required
def create_task():
    db = get_db()
    data = request.json
    
    required_fields = ['project_id', 'title']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        task_data = {
            'project_id': data['project_id'],
            'title': data['title'],
            'description': data.get('description', ''),
            'status': data.get('status', 'To Do'),
            'priority': data.get('priority', 'Medium'),
            'story_points': data.get('story_points', 1)
        }
        
        if data.get('assignee_id'):
            task_data['assignee_id'] = data['assignee_id']
            
        if data.get('due_date'):
            task_data['due_date'] = data['due_date']
            
        res = db.table('tasks').insert(task_data).execute()
        return jsonify({"task": res.data[0]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    db = get_db()
    data = request.json
    
    try:
        # Prevent overriding ID
        update_data = {k: v for k, v in data.items() if k not in ['id', 'project_id', 'created_at']}
        
        res = db.table('tasks').update(update_data).eq('id', task_id).execute()
        if not res.data:
            return jsonify({"error": "Task not found"}), 404
            
        return jsonify({"task": res.data[0]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    db = get_db()
    try:
        res = db.table('tasks').delete().eq('id', task_id).execute()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
