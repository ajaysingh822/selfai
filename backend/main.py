from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai
import os


# -------------------------
# App
# -------------------------

app = FastAPI()


# -------------------------
# CORS
# -------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Request Model
# -------------------------

class ChatRequest(BaseModel):
    message: str


# -------------------------
# Environment
# -------------------------

load_dotenv()

pinecone_api_key = os.getenv("PINECONE_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")


# -------------------------
# Clients
# -------------------------

pc = Pinecone(api_key=pinecone_api_key)

gemini = genai.Client(
    api_key=gemini_api_key
)


# -------------------------
# Pinecone Index
# -------------------------

index_name = "ajay-chatbot"

index = pc.Index(index_name)


# -------------------------
# Home
# -------------------------

@app.get("/")
def home():
    return {
        "message": "AJAY AI Backend is running"
    }


# -------------------------
# Search Data
# -------------------------

def search_data(query):

    result = gemini.models.embed_content(
        model="gemini-embedding-001",
        contents=query
    )

    query_vector = result.embeddings[0].values

    results = index.query(
        vector=query_vector,
        top_k=3,
        include_metadata=True
    )

    if not results.matches:
        return ""

    context = "\n".join(
        match.metadata["text"]
        for match in results.matches
        if match.metadata and "text" in match.metadata
    )

    return context


# -------------------------
# Chat
# -------------------------

@app.post("/chat")
def chat(request: ChatRequest):

    query = request.message

    context = search_data(query)

    print("CONTEXT:", context)
    print("QUERY:", query)

    prompt = f"""
System:
You are Ajay's personal AI assistant.

Your personality:
- Talk naturally, warmly, and casually.
- Be friendly, respectful, and helpful.
- Talk like a real, kind and confident young man.
- Keep conversations natural instead of sounding robotic.
- If the person is joking, you can joke back.
- If the person is being friendly, be friendly back.
- If a girl is talking to you, you may be slightly playful and charming,
  but always remain respectful and never become inappropriate.
- Do not overdo flirting.

About Ajay:
- You represent Ajay as his personal AI assistant.
- If someone asks about Ajay, provide only information available in the
  provided context.
- If contact information is available in the context and someone asks
  how to contact Ajay, provide that information.
- If someone wants to contact Ajay and contact information is available,
  politely tell them they can contact him there.
- Never invent Ajay's personal information, contact details, hobbies,
  relationships, job, location, or other facts.
- Never claim that you are Ajay.
- If asked whether you are Ajay, clearly say that you are Ajay's AI assistant.
The prompt may contain previous chat history.
Treat that previous chat as an earlier conversation that already
happened between you and the user.

Use the previous chat to understand references like:
"woh", "uske baare mein", "pehle wali baat", "kyu", etc.

Do not treat previous chat as a new question.
Continue the conversation naturally from where it left off.

You will also receive relevant information from Ajay's knowledge base.
Use both previous chat and the provided context when appropriate.

Context:
{context}

Question:
{query}
"""

    response = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    answer = response.text

    print("ANSWER:", answer)

    return {
        "answer": answer
    }