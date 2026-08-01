from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import ROLE_COLLECTIONS
from backend.rag_engine import is_analytical_question, sql_rag_chain, hybrid_rag_chain

app = FastAPI(title="MediBot Backend API")

# Enable CORS for Next.js frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock user database
USERS_DB = {
    "dr.mehta": {"password": "password123", "role": "doctor"},
    "nurse.priya": {"password": "password123", "role": "nurse"},
    "billing.ravi": {"password": "password123", "role": "billing_executive"},
    "tech.anand": {"password": "password123", "role": "technician"},
    "admin.sys": {"password": "password123", "role": "admin"},
}

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    question: str
    role: str

@app.post("/login")
def login(req: LoginRequest):
    user = USERS_DB.get(req.username.lower())
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Return a mock token that encodes the username and role
    mock_token = f"mock_token_{user['role']}_{req.username}"
    return {
        "token": mock_token,
        "role": user["role"],
        "username": req.username
    }

@app.post("/chat")
def chat(req: ChatRequest):
    role = req.role.lower()
    if role not in ROLE_COLLECTIONS:
         raise HTTPException(status_code=400, detail=f"Invalid user role: {role}")
         
    question = req.question.strip()
    if not question:
         raise HTTPException(status_code=400, detail="Question cannot be empty")
         
    # 1. Routing decision: is it analytical/numbers query?
    is_sql = is_analytical_question(question)
    
    if is_sql:
        # 2. Check RBAC for analytical queries
        if role in ["billing_executive", "admin"]:
            print(f"Routing to SQL RAG for role '{role}': {question}")
            result = sql_rag_chain(question)
            result["role"] = role
            return result
        else:
            # Block and return custom refusal message
            accessible_cols = ROLE_COLLECTIONS.get(role, [])
            cols_str = ", ".join(accessible_cols)
            refusal_text = (
                f"As a {role}, you do not have authorization to query the financial or maintenance database records. "
                f"I can only answer questions by searching your permitted document collections: {cols_str}."
            )
            return {
                "answer": refusal_text,
                "sources": [],
                "retrieval_type": "blocked",
                "role": role
            }
    else:
        # 3. Handle standard document query with RBAC
        print(f"Routing to Hybrid RAG for role '{role}': {question}")
        result = hybrid_rag_chain(question, role)
        result["role"] = role
        return result

@app.get("/collections/{role}")
def get_collections(role: str):
    role_lower = role.lower()
    if role_lower not in ROLE_COLLECTIONS:
        raise HTTPException(status_code=400, detail="Invalid user role")
    return {
        "role": role_lower,
        "collections": ROLE_COLLECTIONS[role_lower]
    }

@app.get("/health")
def health():
    return {"status": "ok"}
