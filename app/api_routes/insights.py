import os
import json
import requests
from flask import Blueprint, jsonify, g
from app.auth.routes import login_required
from app.database import get_db

bp = Blueprint('api_insights', __name__, url_prefix='/api/projects')

def generate_health_summary(project, tasks, team):
    """Call Groq API to get health summaries and risk predictions."""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return {"error": "Groq API key not configured"}
        
    prompt = f"""
You are a Senior Technical Project Manager and AI Assistant.
Analyze this project and return actionable insights in strictly valid JSON format.

Project Name: {project['name']}
Status: {project['status']}
Deadline: {project['duration']}
Tasks: {len(tasks)} total, {len([t for t in tasks if t['status']=='Completed'])} completed, {len([t for t in tasks if t['status']=='Blocked'])} blocked.
Team Size: {len(team)}

Provide insights on:
1. "health_summary": A 2-sentence summary of project health.
2. "risks": A list of strings identifying potential risks or bottlenecks based on blocked tasks or upcoming deadlines.
3. "recommendations": A list of strings with next best actions.
4. "suggested_health_score": One of ["Green", "Yellow", "Red"].

Return ONLY valid JSON.
"""

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'llama3-8b-8192',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.2,
        'response_format': {'type': 'json_object'}
    }
    
    try:
        response = requests.post('https://api.groq.com/openai/v1/chat/completions', headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return json.loads(content)
    except Exception as e:
        print(f"Groq API Error: {e}")
        return {"error": "Failed to generate AI insights."}

@bp.route('/<int:project_id>/insights', methods=['GET'])
@login_required
def get_project_insights(project_id):
    db = get_db()
    
    try:
        # Fetch Project
        proj_res = db.table('projects').select('*').eq('id', project_id).eq('created_by', g.user['id']).execute()
        if not proj_res.data:
            return jsonify({"error": "Project not found"}), 404
        project = proj_res.data[0]
        
        # Fetch Tasks
        task_res = db.table('tasks').select('*').eq('project_id', project_id).execute()
        tasks = task_res.data
        
        # Fetch Team
        team_res = db.table('assignments').select('*').eq('project_id', project_id).execute()
        team = team_res.data
        
        # Generate Insights
        insights = generate_health_summary(project, tasks, team)
        
        return jsonify({"insights": insights}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
