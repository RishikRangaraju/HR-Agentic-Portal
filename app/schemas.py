from __future__ import annotations
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator
from .enums import Department, EmploymentType


class EmployeeInfo(BaseModel):
    employee_id: str = Field(..., description="Immutable unique identifier")
    first_name: str = Field(..., min_length=1, max_length=64)
    last_name: str = Field(..., min_length=1, max_length=64)
    email: EmailStr
    date_of_birth: date
    hire_date: date
    department: Department
    manager_id: Optional[str] = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME

    @model_validator(mode="after")
    def check_hire_after_birth(self) -> "EmployeeInfo":
        if self.hire_date <= self.date_of_birth:
            raise ValueError("hire_date must be after date_of_birth")
        return self


class ValidateRequest(BaseModel):
    payload: EmployeeInfo = Field(..., description="Employee data to validate")

class ChatRequest(BaseModel):
    message: str
    history: list = []