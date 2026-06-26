# app/tools.py
from sqlmodel import Session, create_engine, select, or_
from sqlalchemy import func
from app.models import EmployeeDB
from app.schemas import EmployeeInfo

engine = create_engine("sqlite:///./employees.db")

def fetch_employee(employee_id: str) -> dict:
    with Session(engine) as session:
        stmt = select(EmployeeDB).where(EmployeeDB.employee_id == employee_id)
        result = session.exec(stmt).first()
        return {"found": bool(result), "record": result.model_dump() if result else None}

# app/tools.py - Update these functions

def create_employee(**kwargs) -> dict: # Changed to **kwargs
    try:
        # kwargs is already a dictionary, so we pass it directly to Pydantic
        emp_model = EmployeeInfo(**kwargs)
        db_obj = EmployeeDB(**emp_model.model_dump())
        with Session(engine) as session:
            session.add(db_obj)
            session.commit()
        return {"created": True, "employee_id": kwargs.get("employee_id")}
    except Exception as e:
        return {"error": f"Invalid data: {str(e)}"}

def update_employee(**kwargs) -> dict: # Changed to **kwargs
    employee_id = kwargs.get("employee_id")
    if not employee_id:
        return {"success": False, "error": "employee_id is required for updates"}
    
    with Session(engine) as session:
        stmt = select(EmployeeDB).where(EmployeeDB.employee_id == employee_id)
        employee = session.exec(stmt).first()
        if not employee: 
            return {"success": False, "error": "Employee not found"}
        
        changed = False
        for key, value in kwargs.items():
            if key != "employee_id" and hasattr(employee, key):
                if getattr(employee, key) != value:
                    setattr(employee, key, value)
                    changed = True
        
        if not changed: 
            return {"success": False, "message": "No changes detected."}
            
        session.add(employee)
        session.commit()
        return {"success": True, "message": f"Employee {employee_id} updated."}

def delete_employee(employee_id: str) -> dict:
    with Session(engine) as session:
        stmt = select(EmployeeDB).where(EmployeeDB.employee_id == employee_id)
        employee = session.exec(stmt).first()
        if not employee: return {"success": False, "error": "Employee not found"}
        session.delete(employee)
        session.commit()
        return {"success": True, "message": f"Employee {employee_id} deleted."}

def search_employees(name_query: str) -> dict:
    with Session(engine) as session:
        search_words = name_query.split()
        conditions = []
        for word in search_words:
            conditions.append(EmployeeDB.first_name.ilike(f"%{word}%"))
            conditions.append(EmployeeDB.last_name.ilike(f"%{word}%"))
        stmt = select(EmployeeDB).where(or_(*conditions))
        results = session.exec(stmt).all()
        if not results: return {"found": False, "message": "No employees found."}
        return {"found": True, "results": [{"employee_id": e.employee_id, "name": f"{e.first_name} {e.last_name}"} for e in results]}

def count_employees() -> dict:
    with Session(engine) as session:
        return {"total_employees": session.exec(select(func.count()).select_from(EmployeeDB)).one()}

def list_employees() -> dict:
    with Session(engine) as session:
        results = session.exec(select(EmployeeDB)).all()
        return {
            "employees": [
                {
                    "employee_id": e.employee_id, 
                    "name": f"{e.first_name} {e.last_name}",
                    "date_of_birth": str(e.date_of_birth) # <--- ADD THIS
                } 
                for e in results
            ]
        }

def get_current_date() -> dict:
    return {"current_date": "June 2026"}

# Mapping for the Tool Node
TOOL_MAP = {
    "fetch_employee": fetch_employee,
    "create_employee": create_employee,
    "update_employee": update_employee,
    "delete_employee": delete_employee,
    "search_employees": search_employees,
    "count_employees": count_employees,
    "list_employees": list_employees,
    "get_current_date": get_current_date,
}

# app/tools.py

from sqlalchemy import func # Ensure func is imported

# ... keep your existing tools ...

def get_department_stats() -> dict:
    """Returns the number of employees in each department."""
    with Session(engine) as session:
        # SQL: SELECT department, count(employee_id) FROM employee GROUP BY department
        stmt = select(EmployeeDB.department, func.count(EmployeeDB.employee_id)).group_by(EmployeeDB.department)
        results = session.exec(stmt).all()
        
        stats = {dept: count for dept, count in results}
        return {"department_counts": stats}

def get_employment_type_stats() -> dict:
    """Returns the number of employees by employment type (Full-time, Part-time, etc)."""
    with Session(engine) as session:
        stmt = select(EmployeeDB.employment_type, func.count(EmployeeDB.employee_id)).group_by(EmployeeDB.employment_type)
        results = session.exec(stmt).all()
        
        stats = {etype: count for etype, count in results}
        return {"employment_type_counts": stats}

def get_age_statistics() -> dict:
    """Calculates the oldest and youngest employee in the system."""
    with Session(engine) as session:
        # Fetch all DOBs to calculate age in Python (since SQLite date math is limited)
        stmt = select(EmployeeDB.first_name, EmployeeDB.last_name, EmployeeDB.date_of_birth)
        results = session.exec(stmt).all()
        
        if not results:
            return {"error": "No employees found to calculate statistics."}
        
        # Use the current reference date (June 2026)
        from datetime import datetime
        current_year = 2026
        
        ages = []
        names = []
        for first, last, dob in results:
            if dob:
                year = int(str(dob).split('-')[0])
                ages.append(current_year - year)
                names.append(f"{first} {last}")
        
        if not ages:
            return {"error": "No valid dates of birth found."}
            
        max_age = max(ages)
        min_age = min(ages)
        
        return {
            "oldest_age": max_age,
            "youngest_age": min_age,
            "oldest_person": names[ages.index(max_age)],
            "youngest_person": names[ages.index(min_age)],
            "average_age": sum(ages) / len(ages)
        }

# IMPORTANT: Update your TOOL_MAP at the bottom of tools.py
TOOL_MAP = {
    "fetch_employee": fetch_employee,
    "create_employee": create_employee,
    "update_employee": update_employee,
    "delete_employee": delete_employee,
    "search_employees": search_employees,
    "count_employees": count_employees,
    "list_employees": list_employees,
    "get_current_date": get_current_date,
    # New Analyst Tools
    "get_department_stats": get_department_stats,
    "get_employment_type_stats": get_employment_type_stats,
    "get_age_statistics": get_age_statistics,
}