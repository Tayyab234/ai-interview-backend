from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import json
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from datetime import datetime

MONGO_URL = "mongodb://localhost:27017"

client = AsyncIOMotorClient(MONGO_URL)

database = client.AIinterviewdb
session = database.get_collection("session")
users = database.get_collection("users") 
chats = database.get_collection("chat") 

#Functions for operations in  database
async def update_session_state(
    session_id: str,
    current_question: int,
    section_index: int,
    question_in_section: int
):
    await session.update_one(
        {"_id": ObjectId(session_id)},
        {
            "$set": {
                "current_question": current_question,
                "section_index": section_index,
                "question_in_section": question_in_section
            }
        }
    )

#-----------------------------------------------------------------------------------------------------

async def add_message(
    session_id: str,
    role: str,
    content: str,
    msg_type: str
):
    await chats.update_one(
        {"session_id": session_id},
        {
            "$push": {
                "messages": {
                    "role": role,
                    "type": msg_type,
                    "content": content,
                    "timestamp": datetime.utcnow()
                }
            }
        }
    )

#-------------------------------------------------------------------------------------------------------------
async def load_chat_if_empty(session_id: str, chat=None):
    if chat is not None and len(chat) > 0:
        return chat

    chat_doc = await chats.find_one({"session_id": session_id})
    if not chat_doc:
        return chat

    messages = chat_doc.get("messages", [])
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        msg_type = msg.get("type", "")  # optional, in case you need it later

        # Ensure content is always a string
        if isinstance(content, dict) or isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False)

        # Map role to LangChain message classes
        if role == "system":
            chat.append(SystemMessage(content=content))
        elif role == "user":
            chat.append(HumanMessage(content=content))
        elif role == "assistant":
            chat.append(AIMessage(content=content))
        else:
            # Unknown role → store as human message by default
            chat.append(HumanMessage(content=content))

    return chat