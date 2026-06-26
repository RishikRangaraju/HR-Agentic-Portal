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