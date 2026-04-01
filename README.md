# ai-interview-backend
# AI-Based Interview System (Backend)

This is the **backend** of an AI-powered interview system built using **Python** and **FastAPI**. The system leverages AI models to conduct interviews, provide feedback, and allow users to resume their interview sessions from where they left off. It uses **LangChain** and **OpenAI** for generating interview questions and evaluating answers.

---

## Features

- **User Authentication**: Secure login and signup with JWT-based authentication.
- **Session Management**: 
  - Create new interview sessions.
  - Resume previous interviews with the `resumeInterview` endpoint.
  - Delete sessions and users.
- **Interview Flow**: 
  - Provides users with questions based on previous progress.
  - Evaluates answers and gives feedback.
- **Persistent Storage**: Uses **MongoDB** to store users, sessions, and chat history.
- **Security**: Passwords are hashed for secure storage.
- **RESTful API**: Multiple endpoints for user and session management, interview handling, and chat history retrieval.

---

## Technologies Used

- **Python 3.11+**
- **FastAPI** – Web framework for building APIs
- **MongoDB** – Database for storing users, sessions, and chats
- **Pydantic** – Data validation and modeling
- **JWT** – Authentication and security
- **LangChain & OpenAI API** – AI model integration for interview questions and answer evaluation
- **Hashlib / bcrypt** – Password hashing

---

## Endpoints

- `POST /signup` – Register a new user
- `POST /login` – Authenticate a user and get JWT token
- `POST /create-session` – Start a new interview session
- `POST /resume-interview` – Resume the last interview session
- `DELETE /delete-session/{session_id}` – Delete a specific session
- `DELETE /delete-user/{user_id}` – Delete a user and all related sessions
- `GET /get-all-chats/{user_id}` – Retrieve all chat history of a user

---

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ai-interview-backend.git
cd ai-interview-backend
