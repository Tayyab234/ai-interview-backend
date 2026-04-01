from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from prompts import prompt1,prompt2,prompt3,prompt4
from mongodb import session,update_session_state,add_message,load_chat_if_empty
from fastapi import HTTPException
from MODEL import llm
from bson import ObjectId
from pydantic_models import InterviewResponse,InterviewPlan,Question
def plan_to_paragraph(plan) -> str:
    text = f"""
This interview consists of {plan.total_questions} questions.

It is divided into the following sections:
"""

    for section in plan.sections:
        text += f"""
- {section.name}: {section.question_count} questions
  Skills: {", ".join(section.skills)}
"""

    return text

#____________________________________________________________________________________________________________________

def build_prompt(data,chat):
    system_prompt = prompt1.format(
    role=data.role,
    interview_type=data.interview_type,
    difficulty_level=data.difficulty_level,
    interview_length=data.interview_length,
    context=data.context,
    interview_mode=data.interview_mode
)
    
    chat.append(SystemMessage(content=system_prompt))
    return system_prompt

#______________________________________________________________________________________________________________________

async def interview_plan(session_id: str,chat):
    await load_chat_if_empty(session_id,chat)
    # 🔹 Fetch session
    session_doc = await session.find_one({"_id": ObjectId(session_id)})
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")

    # 🔹 Generate structured plan
    model = llm.with_structured_output(InterviewPlan)
    plan = model.invoke(chat)

    # 🔹 Update DB with plan + state
    await session.update_one(
        {"_id": ObjectId(session_id)},
        {
            "$set": {
                "sections": [s.model_dump() for s in plan.sections],
                "max_questions": plan.total_questions,
            }
        }
    )

    # 🔹 Optional: keep in chat (context for LLM)
    chat.append(AIMessage(content=plan.model_dump_json()))
    result1=plan_to_paragraph(plan)
    #adding message
    await add_message(session_id,role="assistant",content=result1,msg_type="Plan")
   
    return {
        "Response": "Your plan has been generated click yes to start an interview"
    }

#---------------------------------------------------------------------------------------------------------------

async def start_interview(session_id: str,chat):
    await load_chat_if_empty(session_id,chat)
    session_doc = await session.find_one({"_id": ObjectId(session_id)})
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_doc.get("sections"):
        raise HTTPException(status_code=400, detail="Interview plan not initialized")

    await update_session_state(session_id,current_question=1,section_index=0,question_in_section=1)

    current_section = session_doc["sections"][0]
    formatted_prompt2 = prompt2.format(name=current_section["name"],
                                       skills=", ".join(current_section["skills"]) )                                     
    chat.append(HumanMessage(content=formatted_prompt2))
    
    model1=llm.with_structured_output(Question)
    result = model1.invoke(chat)
    chat.append(AIMessage(result.Question))
    
    #adding message
    await add_message(session_id,role="assistant",content=result.Question,msg_type="question")
   
    return {"question": result.Question}

#--------------------------------------------------------------------------------------------------------------------

async def answer_question(session_id: str, ans: str,chat,new=1):
    await load_chat_if_empty(session_id,chat)
    session_doc = await session.find_one({"_id": ObjectId(session_id)})
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")

    #adding message
    if new:
        chat.append(HumanMessage(content=ans))
        await add_message(session_id,role="user",content=ans,msg_type="answer")
   
    current_question = session_doc["current_question"]
    max_questions = session_doc["max_questions"]
    section_index = session_doc["section_index"]
    question_in_section = session_doc["question_in_section"]
    sections = session_doc["sections"]

    # ✅ Finish interview
    if current_question >= max_questions:
        
        await session.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "finished"}}
        )
        filled_prompt = prompt4.format()
        chat.append(HumanMessage(content=filled_prompt))
        result = llm.invoke(chat)
        chat.pop()
        #adding messages
        await add_message(session_id,role="assistant",content=result.content,msg_type="feedback&Evaluation")
        chat.append(AIMessage(result.content))
        
       
        return {"summary": result.content}

    # ✅ Get current section
    current_section = sections[section_index]

    # ✅ Increment counters
    current_question += 1
    question_in_section += 1

    # ✅ Section switching
    if question_in_section > current_section["question_count"]:
        section_index += 1
        question_in_section = 1

        if section_index < len(sections):
            current_section = sections[section_index]

    # ✅ Save updated state
    await update_session_state(session_id,current_question,section_index,question_in_section)

    # ✅ Generate next question
    model1 = llm.with_structured_output(InterviewResponse)
    
    formatted_prompt3 = prompt3.format(
    name=current_section["name"],
    skills=", ".join(current_section["skills"]),  # list → string
    question_in_section=question_in_section,
    question_count=current_section["question_count"]
)
    chat.append(HumanMessage(content=formatted_prompt3))
    
    result = model1.invoke(chat)
    chat.pop()
    #adding messages
    await add_message(session_id,role="assistant",content=result.dict(),msg_type="feedback & next question")
    chat.append(AIMessage(content=result.model_dump_json()))
    
    return {
        "feedback": result.feedback,
        "rating": result.rating,
        "next_question": result.next_question
    }

    