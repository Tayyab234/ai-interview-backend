from pydantic import BaseModel, EmailStr,Field
from typing import Optional,List

class Section(BaseModel):
    name: str
    question_count: int
    skills: List[str]
class InterviewRequest(BaseModel):
    role: str
    interview_type: Optional[str] = "Technical"
    difficulty_level: Optional[str] = "Medium"
    interview_length: Optional[int] = 15
    context: Optional[str] = "General interview scenario"
    interview_mode: Optional[str] = "Q&A"
class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    role: str
    interview_type: str
    difficulty_level: str
    interview_length: int
    context: str
    interview_mode: str

    status: str

    current_question: int
    max_questions: int

    section_index: int
    question_in_section: int

    sections: List[Section] = []
class answer(BaseModel):
    answer:str=Field(...,description="The answer of the required question")

class InterviewResponse(BaseModel):
    feedback: str = Field(..., description="Evaluation of the answer and improvements")
    rating: int = Field(..., description="Rating from 1 to 10")
    next_question: str = Field(..., description="Next question according to the plan")
class InterviewPlan(BaseModel):
    total_questions: int
    sections: List[Section]
class Question(BaseModel):
    Question:str= Field(..., description="Ask the question according to the plan")

class ResumeRequest(BaseModel):
    session_id: str
    answer: Optional[str] = None

# For signup
class UserSignup(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    age: Optional[int] = Field(None, ge=10, le=100)

# For login
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# For response (avoid sending password)
class UserResponse(BaseModel):
    username: str
    email: EmailStr
    age: Optional[int]