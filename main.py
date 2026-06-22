import os

os.environ["NO_PROXY"] = "*" 
os.environ["no_proxy"] = "*"
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

from dotenv import load_dotenv
load_dotenv() 

import json
import uuid
import logging
from datetime import date
from typing import Optional, Dict, Literal
from app.schemas import ValidateRequest, EmployeeInfo, ChatRequest
from fastapi import FastAPI, HTTPException, APIRouter, status, Depends, Header
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlmodel import Session, SQLModel, create_engine, select, or_
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.enums import Department, EmploymentType
from app.schemas import ValidateRequest, EmployeeInfo
from app.models import EmployeeDB
from agent import run_agentic_workflow

API_KEY = os.getenv("EMPLOYEE_API_KEY")

def verify_api_key(x_api_key: str = Header(...)):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or missing API key"
        )

engine = create_engine("sqlite:///./employees.db")
SQLModel.metadata.create_all(engine)

def fetch_employee(employee_id: str) -> dict:
    with Session(engine) as session:
        stmt = select(EmployeeDB).where(EmployeeDB.employee_id == employee_id)
        result = session.exec(stmt).first()
        return {"found": bool(result), "record": result.model_dump() if result else None}

def create_employee(employee: EmployeeInfo) -> dict:
    db_obj = EmployeeDB(**employee.model_dump())
    with Session(engine) as session:
        session.add(db_obj)
        session.commit()
    return {"created": True, "employee_id": employee.employee_id}

def update_employee(employee_id: str, updates: dict) -> dict:
    with Session(engine) as session:
        stmt = select(EmployeeDB).where(EmployeeDB.employee_id == employee_id)
        employee = session.exec(stmt).first()
        if not employee:
            return {"success": False, "error": "Employee not found"}
        
        changed = False
        for key, value in updates.items():
            if hasattr(employee, key):
                current_val = getattr(employee, key)
                if current_val != value:
                    setattr(employee, key, value)
                    changed = True
        
        if not changed:
            return {"success": False, "message": "No changes detected; the record is already up to date."}
        
        session.add(employee)
        session.commit()
        return {"success": True, "message": f"Employee {employee_id} updated successfully"}

def delete_employee(employee_id: str) -> dict:
    with Session(engine) as session:
        stmt = select(EmployeeDB).where(EmployeeDB.employee_id == employee_id)
        employee = session.exec(stmt).first()
        if not employee:
            return {"success": False, "error": "Employee not found"}
        
        session.delete(employee)
        session.commit()
        return {"success": True, "message": f"Employee {employee_id} deleted successfully"}


def search_employees(name_query: str) -> dict:
    with Session(engine) as session:
        search_words = name_query.split()
        
        conditions = []
        for word in search_words:
            conditions.append(EmployeeDB.first_name.ilike(f"%{word}%"))
            conditions.append(EmployeeDB.last_name.ilike(f"%{word}%"))
        
        stmt = select(EmployeeDB).where(or_(*conditions))
        results = session.exec(stmt).all()
        
        if not results:
            return {"found": False, "message": f"No employees found matching '{name_query}'"}
        
        employee_list = [
            {"employee_id": e.employee_id, "name": f"{e.first_name} {e.last_name}"} 
            for e in results
        ]
        return {"found": True, "results": employee_list}

app = FastAPI(title="Agentic Employee Validator API")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print("\n--- !!! VALIDATION ERROR DETECTED !!! ---")
    print(f"Error Details: {exc.errors()}")
    print("------------------------------------------\n")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

log = logging.getLogger("employee_agent")
log.setLevel(logging.INFO)

router = APIRouter()

@router.get("/", name="health", operation_id="health_check")
async def health():
    return {"status": "ok", "message": "Agent server is alive"}

@router.post(
    "/validate",
    name="validate_employee",
    operation_id="validate_employee",
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Pydantic validation error"},
        500: {"description": "Unexpected server error"},
    },
)
async def validate_employee(req: ValidateRequest):
    run_id = str(uuid.uuid4())
    log.info(f"[run {run_id}] Agentic request received")
    employee = req.payload 

    def tool_executor(name: str, args: dict):
        log.info(f"Executing tool: {name} with args: {args}")
        if name == "fetch_employee":
            return fetch_employee(args.get("employee_id"))
        elif name == "create_employee":
            try:
                emp_model = EmployeeInfo(**args)
                return create_employee(emp_model)
            except Exception as e:
                return {"error": f"Invalid data: {str(e)}"}
        elif name == "update_employee":
            emp_id = args.get("employee_id")
            updates = {k: v for k, v in args.items() if k != "employee_id"}
            return update_employee(emp_id, updates)
        elif name == "delete_employee":
            return delete_employee(args.get("employee_id"))
        elif name == "search_employees":
            return search_employees(args.get("name_query"))
        return {"error": f"Tool {name} not recognized."}

    user_prompt = f"Please process the following employee record: {employee.model_dump_json()}"
    try:
        final_answer, _ = run_agentic_workflow(user_prompt, tool_executor)
    except Exception as e:
        log.error(f"[run {run_id}] Agent crashed: {e}")
        raise HTTPException(status_code=500, detail=f"AI Agent Error: {str(e)}")

    return {
        "run_id": run_id,
        "status": "ok",
        "agent_response": final_answer,
        "validated_data": jsonable_encoder(employee),
    }

@router.post(
    "/chat",
    name="chat_with_agent",
    operation_id="chat_with_agent",
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_200_OK,
)
async def chat_with_agent(req: ChatRequest):
    run_id = str(uuid.uuid4())
    log.info(f"[run {run_id}] Chat request received")

    def tool_executor(name: str, args: dict):
        log.info(f"Executing tool: {name} with args: {args}")
        if name == "fetch_employee":
            return fetch_employee(args.get("employee_id"))
        elif name == "create_employee":
            try:
                emp_model = EmployeeInfo(**args)
                return create_employee(emp_model)
            except Exception as e:
                return {"error": f"Invalid data: {str(e)}"}
        elif name == "update_employee":
            emp_id = args.get("employee_id")
            updates = {k: v for k, v in args.items() if k != "employee_id"}
            return update_employee(emp_id, updates)
        elif name == "delete_employee":
            return delete_employee(args.get("employee_id"))
        elif name == "search_employees":
            return search_employees(args.get("name_query"))
        return {"error": f"Tool {name} not recognized."}

    try:
        final_answer, updated_history = run_agentic_workflow(
            req.message, 
            tool_executor, 
            history=req.history
        )
    except Exception as e:
        log.error(f"[run {run_id}] Agent crashed: {e}")
        raise HTTPException(status_code=500, detail=f"AI Agent Error: {str(e)}")

    return {
        "run_id": run_id,
        "agent_response": final_answer,
        "history": updated_history 
    }

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)