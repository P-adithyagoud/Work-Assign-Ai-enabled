import csv
import io
from app.models.employee import employee_exists, insert_employee
from app.utils import normalize_employee, validate_employee

EXPECTED_HEADERS = [
    "employee_id", "name", "skills", "experience",
    "role", "availability", "performance_score",
]


def parse_employee_csv(file_storage):
    content = file_storage.stream.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []

    missing = [h for h in EXPECTED_HEADERS if h not in headers]
    if missing:
        return {
            "total_uploaded": 0,
            "added": 0,
            "duplicates": 0,
            "validation_failures": len(missing),
            "errors": [f"Missing required column: {col}" for col in missing],
        }

    total_uploaded = 0
    added = 0
    duplicates = 0
    validation_failures = 0
    errors = []
    seen_in_file = set()

    for index, row in enumerate(reader, start=2):
        total_uploaded += 1
        row_errors = validate_employee(row)
        employee_id = str(row.get("employee_id", "")).strip()

        if employee_id in seen_in_file or (employee_id and employee_exists(employee_id)):
            duplicates += 1
            errors.append(f"Row {index}: duplicate employee_id {employee_id}.")
            continue

        if row_errors:
            validation_failures += 1
            errors.append(f"Row {index}: {' '.join(row_errors)}")
            continue

        employee = normalize_employee(row)
        seen_in_file.add(employee["employee_id"])
        insert_employee(employee)
        added += 1

    return {
        "total_uploaded": total_uploaded,
        "added": added,
        "duplicates": duplicates,
        "validation_failures": validation_failures,
        "errors": errors[:25],
    }
