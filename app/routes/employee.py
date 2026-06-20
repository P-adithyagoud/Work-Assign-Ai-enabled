from flask import Blueprint, request

from app.models.employee import distinct_roles, list_employees
from app.routes.auth import login_required
from app.utils.csv_parser import parse_employee_csv


employee_bp = Blueprint("employee", __name__)


@employee_bp.post("/upload-csv")
@login_required
def upload_csv():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".csv"):
        return {"ok": False, "error": "Please upload a CSV file."}, 400
    result = parse_employee_csv(file)
    return {"ok": True, "result": result}


@employee_bp.get("/employees")
@login_required
def employees():
    rows = list_employees(
        search=request.args.get("search", ""),
        role=request.args.get("role", ""),
        availability=request.args.get("availability", ""),
        sort=request.args.get("sort", "performance_desc"),
    )
    employees_json = [dict(row) for row in rows]
    return {"ok": True, "employees": employees_json, "roles": distinct_roles()}
