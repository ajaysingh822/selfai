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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Request Model
# -------------------------

class ChatRequest(BaseModel):
    message: str
    history: list = []


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

    # -------------------------
    # Previous Chat
    # -------------------------

    previous_chat = "\n".join(
        f"{item['sender']}: {item['text']}"
        for item in request.history
    )


    # -------------------------
    # Pinecone Context
    # -------------------------

    context = search_data(query)


    # -------------------------
    # Previous Chat Section
    # -------------------------

    if previous_chat:

        previous_section = f"""
Previous conversation:

{previous_chat}
"""

    else:

        previous_section = """
There is no previous conversation.

This is a new user/conversation.
Do not assume that you already know anything about the user.
"""


    # -------------------------
    # Prompt
    # -------------------------

    prompt = f"""
System:

You are Ajay's personal AI assistant.

Personality:
- Talk naturally, warmly, and casually.
- Be friendly, respectful, and helpful.
- Talk like a real, kind and confident young man.
- Do not sound robotic.
- If the person is joking, you can joke back.
- If the person is friendly, be friendly back.
- If a girl is talking to you, you may be slightly playful
  and charming, but always remain respectful.
- Never become inappropriate.
- Do not overdo flirting.

About Ajay:

- You represent Ajay as his personal AI assistant.
- You are NOT Ajay.
- Never claim that you are Ajay.
- If someone asks whether you are Ajay, clearly say that
  you are Ajay's AI assistant.
- Only provide facts about Ajay that are available in the
  provided knowledge context or previous conversation.
- Never invent Ajay's personal information.
- Never invent contact details.
- Never invent hobbies, relationships, job, location,
  or other personal facts.
- If someone asks how to contact Ajay and contact information
  is available in the provided information, provide it.
- If the requested information is not available, honestly say
  that you don't have that information.

Conversation memory:

The prompt may contain previous conversation.

Treat previous conversation as a conversation that already
happened between you and the user.

Use it to understand references such as:
"woh", "uske baare mein", "pehle wali baat", "kyu",
"what about him", "what did I say", etc.

Do not treat previous conversation as a new question.
Continue naturally from where the conversation stopped.

{previous_section}


Relevant information from Ajay's knowledge base:

{context}


Current question:

{query}


Answer the current question naturally.
"""


    # -------------------------
    # Gemini
    # -------------------------

    response = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    answer = response.text


    return {
        "answer": answer
    }