from __future__ import annotations
from typing import Optional

from sqlmodel import SQLModel, Field

from .enums import Department, EmploymentType


class EmployeeDB(SQLModel, table=True):
    employee_id: str = Field(primary_key=True, index=True)
    first_name: str
    last_name: str
    email: str
    date_of_birth: str
    hire_date: str
    department: Department
    manager_id: Optional[str] = Field(default=None, foreign_key="employeedb.employee_id")
    employment_type: EmploymentType = Field(default=EmploymentType.FULL_TIME)