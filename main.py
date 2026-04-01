from fastapi import FastAPI, HTTPException, Depends,Form
from fastapi.encoders import jsonable_encoder
import datetime
from datetime import timedelta,datetime
import jwt
from bson import ObjectId
#------------------------------------------------------------------------------------------------------------------
from utility_functions import build_prompt,start_interview,interview_plan,answer_question
from jwt_hash import hash_password,verify_password,get_current_user,ALGORITHM,SECRET_KEY,ACCESS_TOKEN_EXPIRE_MINUTES
from mongodb import session,users,chats,add_message,load_chat_if_empty
from pydantic_models import InterviewRequest,SessionResponse,UserSignup,UserLogin,UserResponse,ResumeRequest,Question

app = FastAPI()
chat=list()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#______________________________________________________________________________________________________________________
@app.get("/")
def home():
    return {"message": "AI Interview System API Running"}

#______________________________________________________________________________________________________________________
@app.post("/signup", response_model=UserResponse)
async def signup(user: UserSignup):
    # Check if user exists
    existing = await users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)  # hash password
    await users.insert_one(user_dict)

    return UserResponse(**user_dict)

#______________________________________________________________________________________________________________________
@app.post("/login")
async def login_oauth2(
    username: str = Form(...),
    password: str = Form(...)
):
    existing = await users.find_one({"email": username})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(password, existing["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")

    payload = {
        "user_id": str(existing["_id"]),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}


#______________________________________________________________________________________________________________________

@app.post("/session/create", response_model=SessionResponse)
async def create_session(
    interview: InterviewRequest,
    user_id: str = Depends(get_current_user)   # ✅ get from token
):
    # Check if user exists
    user = await users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Session metadata
    session_doc = {
        "user_id": user_id,
        "role": interview.role,
        "interview_type": interview.interview_type,
        "difficulty_level": interview.difficulty_level,
        "interview_length": interview.interview_length,
        "context": interview.context,
        "interview_mode": interview.interview_mode,

        # State fields
        "status": "paused",   # paused | started | finished
        "current_question": 0,
        "max_questions": 0,
        "section_index": 0,
        "question_in_section": 0,
        "sections": [],

        "created_at": datetime.utcnow()
    }

    result = await session.insert_one(session_doc)

    session_doc["session_id"] = str(result.inserted_id)
    session_doc["user_id"] = str(session_doc["user_id"])
    await chats.insert_one({
    "session_id": session_doc["session_id"],
    "user_id": session_doc["user_id"],
    "messages": []
    } )
    result1=build_prompt(interview,chat)
    #adding message                  
    await add_message(session_doc["session_id"],role="system",content=result1,msg_type="prompt")
    session_obj = SessionResponse(**session_doc)
    return session_obj
    
#______________________________________________________________________________________________________________________
@app.get("/sessions/me")
async def get_sessions(user_id: str = Depends(get_current_user)):
    sessions = await session.find({"user_id": user_id}).to_list(100)

    result = []
    for s in sessions:
        result.append({
            "session_id": str(s["_id"]),
            "role": s["role"],
            "interview_type": s["interview_type"],
            "created_at": s["created_at"],
            "plan_generated": s.get("plan_generated", False)
        })

    return jsonable_encoder(result)
#____________________________________________________________________________________________________________


@app.get("/session-status")
async def get_session_status(session_id: str):
    session_data = await session.find_one({"_id": ObjectId(session_id)})

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": session_data["status"]
    }
#_____________________________________________________________________________________________________________


@app.post("/interview/resume")
async def resume_interview(data:ResumeRequest):

    session_doc = await session.find_one({"_id": ObjectId(data.session_id)})
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")

    chat_doc = await chats.find_one({"session_id": data.session_id})
    last_message = chat_doc["messages"][-1]
    #case1 when interview progression
    if data.answer:
        return await answer_question(
            session_id=data.session_id,
            ans=data.answer,
            chat=chat
        )
    
    #other cases where interview interrupt then continue after interruption
    elif last_message["role"] == "system":
        return await interview_plan(
            session_id=data.session_id,
            chat=chat
        )
        
    elif last_message["role"] == "user":
        return await answer_question(
            session_id=data.session_id,
            ans=last_message["content"],
            chat=chat,
            new=0
        )
    elif last_message["role"] == "assistant"  and last_message["type"]=="Plan":

        return await start_interview(
            session_id=data.session_id,
            chat=chat
        ) 
    return {"message": "Unhandled state"}

#______________________________________________________________________________________________________________________
@app.get("/chat/last")
async def get_last_message(session_id: str):

    chat_doc = await chats.find_one({"session_id": session_id})

    if not chat_doc or len(chat_doc.get("messages", [])) == 0:
        return {"message": None}

    last_message = chat_doc["messages"][-1]

    return {
        "role": last_message["role"],
        "content": last_message["content"],
    }

#______________________________________________________________________________________________________________________

@app.get("/chat/all")
async def get_all_messages(session_id: str):
    # Load chat if empty (your existing logic)
    await load_chat_if_empty(session_id, chat)

    # Prepare messages
    messages_to_return = [
        {"role": type(m).__name__, "content": m.content}
        for m in chat
    ]

    # Return the chat as JSON response
    return {"messages": messages_to_return}

#----------------------------------------------------------------------------------------------------------------------

@app.delete("/delete_user/{user_id}")
async def delete_user(user_id: str):
    # Check if user exists
    user = await users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete all sessions of the user
    sessions = await session.find({"user_id": user_id}).to_list(length=None)
    session_ids = [str(s["_id"]) for s in sessions]

    # Delete chats for each session
    await chats.delete_many({"session_id": {"$in": session_ids}})
    
    # Delete sessions
    await session.delete_many({"user_id": user_id})

    # Delete user
    await users.delete_one({"_id": ObjectId(user_id)})

    return {"message": f"User {user_id} and all their sessions & chats deleted successfully."}

# -------------------------------
# Delete a session and its chats
# -------------------------------
@app.delete("/delete_session/{session_id}")
async def delete_session(session_id: str):
    # Check if session exists
    session_doc = await session.find_one({"_id": ObjectId(session_id)})
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete corresponding chats
    await chats.delete_many({"session_id": session_id})
    
    # Delete session
    await session.delete_one({"_id": ObjectId(session_id)})

    return {"message": f"Session {session_id} and its chats deleted successfully."}