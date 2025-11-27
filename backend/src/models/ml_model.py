from enum import Enum
from pydantic import BaseModel, Field

class PersonHomeOwnership(str, Enum):
    RENT = 'RENT'
    OWN = 'OWN'
    MORTGAGE = 'MORTGAGE'
    OTHER = 'OTHER'

class LoanIntent(str, Enum):
    EDUCATION = 'EDUCATION'
    MEDICAL = 'MEDICAL'
    VENTURE = 'VENTURE'
    PERSONAL = 'PERSONAL'
    DEBTCONSOLIDATION = 'DEBTCONSOLIDATION'
    HOMEIMPROVEMENT = 'HOMEIMPROVEMENT'

class LoanGrade(str, Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'
    F = 'F'
    G = 'G'

class CBPersonDefaultOnFile(str, Enum):
    Y = 'Y'
    N = 'N'

class LoanApplication(BaseModel):
    person_age: int = Field(..., description="Age of the person")
    person_income: float = Field(..., description="Annual income of the person")
    person_home_ownership: PersonHomeOwnership = Field(..., description="Home ownership status")
    person_emp_length: float = Field(..., description="Employment length in years")
    loan_intent: LoanIntent = Field(..., description="Intent of the loan")
    loan_grade: LoanGrade = Field(..., description="Grade of the loan")
    loan_amnt: float = Field(..., description="Loan amount requested")
    loan_int_rate: float = Field(..., description="Interest rate of the loan")
    cb_person_default_on_file: CBPersonDefaultOnFile = Field(..., description="Historical default status")
    cb_person_cred_hist_length: int = Field(..., description="Credit history length in years")
