from enum import Enum

class Department(str, Enum):
    ENGINEERING = "ENGINEERING"
    HR = "HR"
    SALES = "SALES"
    MARKETING = "MARKETING"

class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACTOR = "CONTRACTOR"
    INTERN = "INTERN"