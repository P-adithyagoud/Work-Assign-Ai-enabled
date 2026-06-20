import os
import json
import requests

def generate_mock_explanation(project, team_members):
    """
    Fallback deterministic mock generator that builds realistic explanation texts
    based on the project's needs and the selected team's data.
    Used when the Groq API key is invalid, missing, or when API calls fail.
    """
    proj_techs = [t.strip().lower() for t in project['technologies'].split(',') if t.strip()]
    proj_roles = [r.strip().lower() for r in project['preferred_roles'].split(',') if r.strip()]
    
    # 1. Generate individual explanations
    individual_explanations = {}
    team_skills_set = set()
    avg_perf = 0.0
    avg_exp = 0.0
    
    for emp in team_members:
        emp_skills = [s.strip().lower() for s in emp['skills'].split(',') if s.strip()]
        team_skills_set.update(emp_skills)
        avg_perf += emp['performance_score']
        avg_exp += emp['experience']
        
        # Determine matching skills
        matching_skills = [s for s in emp_skills if s in proj_techs]
        matching_skills_title = [s.title() for s in matching_skills]
        
        # Build explanation string
        role_match_str = ""
        if emp['role'].lower() in proj_roles:
            role_match_str = f"matches the preferred role of '{emp['role']}' and "
            
        skills_str = ""
        if matching_skills_title:
            skills_str = f" offers core skills in {', '.join(matching_skills_title[:3])},"
        else:
            skills_str = " provides a versatile general skillset,"
            
        exp_str = f" bringing {emp['experience']} years of experience."
        perf_str = f" Their high performance score of {emp['performance_score']}% guarantees quality delivery."
        
        explanation = f"{emp['name']} {role_match_str}{skills_str}{exp_str}{perf_str}"
        individual_explanations[str(emp['employee_id'])] = explanation

    if team_members:
        avg_perf /= len(team_members)
        avg_exp /= len(team_members)
    
    # 2. Check for missing skills
    missing_skills = []
    for tech in proj_techs:
        if tech not in team_skills_set:
            missing_skills.append(tech.title())
            
    # 3. Assemble team strengths
    strengths_list = []
    if avg_perf >= 85:
        strengths_list.append("exceptional team performance average")
    if avg_exp >= 6:
        strengths_list.append("strong senior experience depth")
    
    shared_techs = set(proj_techs).intersection(team_skills_set)
    if shared_techs:
        strengths_list.append(f"direct coverage of key technologies like {', '.join([t.title() for t in list(shared_techs)[:3]])}")
    
    if not strengths_list:
        strengths_list.append("balanced distribution of roles and core development skills")
        
    team_strengths = f"The selected team features a {', '.join(strengths_list)}. With an average performance rating of {avg_perf:.1f}% and {avg_exp:.1f} mean years of experience, this team is well-positioned for project implementation."
    
    # 4. Assemble delivery risks
    risks_list = []
    if missing_skills:
        risks_list.append(f"Missing domain expertise in requested technologies: {', '.join(missing_skills)}")
    if avg_exp < 4:
        risks_list.append("Relatively junior average experience level across team members")
    if any(emp['availability'] in ('Unavailable', '0%', '0') for emp in team_members):
        risks_list.append("Potential scheduling constraints identified with partially-available members")
        
    if not risks_list:
        delivery_risks = "No major technical or delivery risks identified. The team matches the requested profile and exhibits high availability."
    else:
        delivery_risks = ". ".join(risks_list)
        
    # 5. Assemble recommendations
    recs_list = []
    if missing_skills:
        recs_list.append(f"Consider running training sessions or allocating an external advisor for {', '.join(missing_skills)}")
    if avg_exp < 5:
        recs_list.append("Introduce periodic architectural reviews to guide the junior development cycle")
    if len(team_members) < project['team_size']:
        recs_list.append("Review project scale or adjust requirements to fill outstanding vacant seats")
        
    recs_list.append("Conduct an initial team alignment meeting to map individual tasks to strengths.")
    recommendations = " ".join(recs_list)

    return {
        "individual_explanations": individual_explanations,
        "team_strengths": team_strengths,
        "delivery_risks": delivery_risks,
        "missing_skills": missing_skills,
        "recommendations": recommendations
    }

def get_ai_explanations(project, team_members):
    """
    Queries Groq API for team composition explanations.
    If the key is not set, or a failure occurs, returns fallback mock explanations.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    
    # Check if API Key is empty or default placeholder
    if not api_key or api_key.startswith("gsk_placeholder"):
        print("Groq API Key is not set or is placeholder. Using local fallback generator.")
        return generate_mock_explanation(project, team_members)
        
    # Structure data payload for prompt
    project_info = {
        "name": project['name'],
        "description": project['description'],
        "technologies": project['technologies'],
        "preferred_roles": project['preferred_roles'],
        "team_size": project['team_size']
    }
    
    candidates = []
    for emp in team_members:
        candidates.append({
            "employee_id": emp['employee_id'],
            "name": emp['name'],
            "role": emp['role'],
            "skills": emp['skills'],
            "experience": emp['experience'],
            "performance_score": emp['performance_score'],
            "availability": emp['availability']
        })
        
    system_prompt = (
        "You are an expert AI workforce management advisor. "
        "Analyze a project and the team selected by a deterministic scoring engine. "
        "Provide a technical assessment of the team. "
        "You must respond ONLY with a raw JSON object (do not include markdown formatting or backticks) containing:\n"
        "1. 'individual_explanations': a dictionary mapping employee_id to a 2-sentence explanation of why they fit the project.\n"
        "2. 'team_strengths': a summary paragraph of the team's combined strengths.\n"
        "3. 'delivery_risks': a summary paragraph of delivery risks or resource constraints.\n"
        "4. 'missing_skills': a list of requested technologies that are missing from the team's skills.\n"
        "5. 'recommendations': a list or paragraph of actionable recommendations to mitigate risks.\n"
        "Do not change the team selections. Explain only the provided candidates."
    )
    
    user_prompt = f"Project: {json.dumps(project_info)}\nSelected Team: {json.dumps(candidates)}"
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=12)
        
        if response.status_code == 200:
            res_json = response.json()
            content = res_json['choices'][0]['message']['content']
            # Clean possible markdown wrap from AI output
            content_cleaned = content.strip().strip('`').replace('json\n', '', 1)
            parsed_explanations = json.loads(content_cleaned)
            
            # Basic validation of returned format
            required_keys = ['individual_explanations', 'team_strengths', 'delivery_risks', 'missing_skills', 'recommendations']
            if all(key in parsed_explanations for key in required_keys):
                return parsed_explanations
            else:
                print("Groq response missing required keys. Using local fallback.")
        else:
            print(f"Groq API returned status code {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"Failed to query Groq API: {str(e)}")
        
    # Return fallback on any failure
    print("Using local fallback explanation generator.")
    return generate_mock_explanation(project, team_members)
