import io
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.auth.routes import login_required
from app.database import get_db

bp = Blueprint('employees', __name__, url_prefix='/employees')

@bp.route('/', methods=('GET',))
@login_required
def index():
    """Render the employee roster page with search and filters."""
    db = get_db()
    
    # Get search and filter query parameters
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    avail_filter = request.args.get('availability', '').strip()
    min_exp = request.args.get('min_experience', '').strip()
    min_perf = request.args.get('min_performance', '').strip()
    
    # Build query
    query = db.table('employees').select('*')
    
    if search:
        query = query.or_(f"name.ilike.%{search}%,skills.ilike.%{search}%,employee_id.ilike.%{search}%")
        
    if role_filter:
        query = query.eq('role', role_filter)
        
    if avail_filter:
        if avail_filter.lower() == 'available':
            query = query.or_("availability.ilike.available,availability.ilike.active,availability.ilike.yes,availability.ilike.true,availability.eq.100%")
        elif avail_filter.lower() == 'unavailable':
            query = query.or_("availability.ilike.unavailable,availability.ilike.inactive,availability.ilike.no,availability.ilike.false,availability.eq.0,availability.eq.0%")
            
    if min_exp:
        try:
            query = query.gte('experience', int(min_exp))
        except ValueError:
            pass
            
    if min_perf:
        try:
            query = query.gte('performance_score', int(min_perf))
        except ValueError:
            pass
            
    # Execute query
    try:
        res = query.order('name').execute()
        employees = res.data
    except Exception as e:
        print(f"Error fetching employees: {e}")
        employees = []
    
    # Get distinct roles for filters
    try:
        roles_res = db.table('employees').select('role').execute()
        roles = sorted(list(set(r['role'] for r in roles_res.data)))
    except Exception:
        roles = []
    
    return render_template(
        'employees.html',
        employees=employees,
        roles=roles,
        search=search,
        selected_role=role_filter,
        selected_availability=avail_filter,
        min_experience=min_exp,
        min_performance=min_perf
    )

def process_employee_csv(stream, db):
    """
    Parses a CSV file stream containing employee details and batch upserts into Supabase.
    Returns a tuple: (imported_count, list_of_error_rows).
    """
    csv_reader = csv.reader(stream)
    
    # Parse headers
    headers = next(csv_reader, None)
    if not headers:
        raise ValueError("The CSV file is empty.")
        
    # Clean headers
    headers = [h.strip().lower() for h in headers]
    
    # Map indices
    id_idx = name_idx = role_idx = skills_idx = exp_idx = avail_idx = perf_idx = -1
    
    for idx, h in enumerate(headers):
        if 'id' in h and ('employee' in h or h == 'id'):
            id_idx = idx
        elif 'name' in h:
            name_idx = idx
        elif 'role' in h or 'title' in h:
            role_idx = idx
        elif 'skills' in h or 'technologies' in h:
            skills_idx = idx
        elif 'experience' in h or 'years' in h:
            exp_idx = idx
        elif 'availability' in h or 'status' in h:
            avail_idx = idx
        elif 'performance' in h or 'score' in h:
            perf_idx = idx
            
    # Validate that crucial columns exist
    missing = []
    if id_idx == -1: missing.append("Employee ID")
    if name_idx == -1: missing.append("Name")
    if role_idx == -1: missing.append("Role")
    if skills_idx == -1: missing.append("Skills")
    if exp_idx == -1: missing.append("Experience (Years)")
    if avail_idx == -1: missing.append("Availability")
    if perf_idx == -1: missing.append("Performance Score")
    
    if missing:
        raise ValueError(f"CSV missing columns: {', '.join(missing)}")
        
    error_rows = []
    records_to_upsert = []
    
    for row_num, row in enumerate(csv_reader, start=2):
        if not row or all(cell.strip() == '' for cell in row):
            continue # Skip empty rows
            
        try:
            # Extract values
            emp_id = row[id_idx].strip()
            name = row[name_idx].strip()
            role = row[role_idx].strip()
            skills = row[skills_idx].strip()
            experience_str = row[exp_idx].strip()
            availability = row[avail_idx].strip()
            performance_str = row[perf_idx].strip()
            
            # Validation
            if not emp_id or not name:
                error_rows.append(f"Row {row_num}: Employee ID and Name cannot be empty.")
                continue
                
            # Parsing numbers
            try:
                experience = int(float(experience_str))
            except ValueError:
                experience = 0
                
            try:
                performance_score = int(float(performance_str))
                # Clamp to [0, 100]
                performance_score = max(0, min(100, performance_score))
            except ValueError:
                performance_score = 0
            
            records_to_upsert.append({
                'employee_id': emp_id,
                'name': name,
                'role': role,
                'skills': skills,
                'experience': experience,
                'availability': availability,
                'performance_score': performance_score
            })
            
        except Exception as row_error:
            error_rows.append(f"Row {row_num}: {str(row_error)}")
            
    if records_to_upsert:
        try:
            # Batch upsert to Supabase
            db.table('employees').upsert(records_to_upsert, on_conflict='employee_id').execute()
        except Exception as e:
            raise ValueError(f"Database upsert failed: {str(e)}")
            
    return len(records_to_upsert), error_rows


@bp.route('/import', methods=('POST',))
@login_required
def import_csv():
    """Parse upload CSV file containing employee details and import/update database entries."""
    next_page = request.args.get('next', '')
    if next_page == 'projects.index':
        redirect_url = url_for('projects.index')
    else:
        redirect_url = url_for('employees.index')

    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(redirect_url)
        
    file = request.files['file']
    if file.filename == '':
        flash('No file selected for uploading.', 'error')
        return redirect(redirect_url)
        
    if not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'error')
        return redirect(redirect_url)

    try:
        # Read the file stream
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        db = get_db()
        imported_count, error_rows = process_employee_csv(stream, db)
        
        if error_rows:
            flash(f"Imported {imported_count} employees. Errors occurred on {len(error_rows)} rows: {'; '.join(error_rows[:5])}...", 'warning')
        else:
            flash(f"Successfully imported {imported_count} employees.", 'success')
            
    except Exception as e:
        flash(f"An error occurred while parsing the CSV file: {str(e)}", 'error')
        
    return redirect(redirect_url)
