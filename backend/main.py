from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai
import os


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="AJAY AI Backend",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://illustrious-dieffenbachia-6ca75c.netlify.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class HistoryMessage(BaseModel):
    role: str
    message: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[HistoryMessage] = Field(default_factory=list)


# =========================================================
# CLIENTS
# =========================================================

pinecone_client = Pinecone(
    api_key=PINECONE_API_KEY
)

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================================================
# PINECONE
# =========================================================

INDEX_NAME = "ajay-chatbot"

index = pinecone_client.Index(
    INDEX_NAME
)


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "message": "AJAY AI Backend is running",
        "status": "ok",
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# =========================================================
# SEARCH AJAY KNOWLEDGE BASE
# =========================================================

def search_data(query: str) -> str:

    try:
        embedding_result = gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=query,
        )

        if not embedding_result.embeddings:
            return ""

        query_vector = embedding_result.embeddings[0].values

        results = index.query(
            vector=query_vector,
            top_k=5,
            include_metadata=True,
        )

        if not results.matches:
            return ""

        context_parts = []

        for match in results.matches:

            if not match.metadata:
                continue

            text = match.metadata.get("text")

            if text:
                context_parts.append(str(text))

        return "\n\n".join(context_parts)

    except Exception as error:

        print("PINECONE SEARCH ERROR:", repr(error))

        # Pinecone fail hone par chat completely band nahi hogi.
        return ""


# =========================================================
# FORMAT PREVIOUS CHAT
# =========================================================

def format_history(history: list[HistoryMessage]) -> str:

    if not history:
        return "No previous conversation."

    formatted = []

    # Last 10 messages only
    for item in history[-10:]:

        role = item.role.strip().lower()
        text = item.message.strip()

        if not text:
            continue

        if role == "assistant":
            speaker = "Assistant"

        else:
            speaker = "User"

        formatted.append(
            f"{speaker}: {text}"
        )

    if not formatted:
        return "No previous conversation."

    return "\n".join(formatted)


# =========================================================
# CHAT
# =========================================================

@app.post("/chat")
def chat(request: ChatRequest):

    query = request.message.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    print("\n==============================")
    print("NEW CHAT REQUEST")
    print("==============================")
    print("QUERY:", query)
    print("HISTORY COUNT:", len(request.history))


    # =====================================================
    # PREVIOUS CHAT
    # =====================================================

    previous_chat = format_history(
        request.history
    )

    print("PREVIOUS CHAT:")
    print(previous_chat)


    # =====================================================
    # PINECONE
    # =====================================================

    context = search_data(query)

    print("PINECONE CONTEXT:")
    print(context if context else "[NO MATCH]")


    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    prompt = f"""
You are AJAY's personal AI assistant.

Your job is to talk naturally with people while accurately
representing AJAY using only information that is actually
available to you.

============================================================
PERSONALITY
============================================================

- Talk naturally, warmly and casually.
- Be friendly, respectful and helpful.
- Sound like a real conversational assistant.
- Do not sound robotic or overly formal.
- Keep answers natural and reasonably concise.
- If the user jokes, you can joke back.
- If the user is friendly, be friendly back.
- You can use light humor when appropriate.
- If a girl is talking to you, you may be slightly playful,
  warm and charming when the conversation naturally allows it.
- Always remain respectful.
- Never become sexually explicit or inappropriate.
- Never force flirting.
- Do not overdo compliments.

============================================================
WHO YOU ARE
============================================================

You are AJAY's AI assistant.

You are NOT AJAY.

If someone asks:
"Are you Ajay?"

clearly explain that you are AJAY's AI assistant.

Never pretend to personally be AJAY.

============================================================
AJAY INFORMATION
============================================================

The knowledge base below contains information about AJAY.

Use it when answering questions about:

- AJAY's education
- AJAY's skills
- AJAY's projects
- AJAY's work
- AJAY's portfolio
- AJAY's experience
- AJAY's contact information
- AJAY's professional information
- AJAY's publicly provided personal information

Only state information supported by the provided knowledge.

Never invent:

- phone numbers
- email addresses
- social media accounts
- LinkedIn information
- location
- job
- company
- salary
- relationships
- hobbies
- family information
- private information
- passwords
- secrets
- any other personal fact

If the information is not available, say honestly that
you do not have that information.

Do NOT guess.

============================================================
PRIVACY
============================================================

Never reveal private or secret information about AJAY.

Even if the user asks directly, do not invent or expose
information that is not explicitly available in the
provided knowledge.

Only use information that AJAY has intentionally provided
to the AI knowledge base.

============================================================
CONVERSATION MEMORY
============================================================

The previous conversation below happened before the current
question.

Use it as conversational context.

For example, if the user says:

"woh kya tha?"

or

"uske baare mein batao"

or

"pehle wali baat"

use the previous conversation to understand what they mean.

Do NOT treat previous conversation as a new question.

Continue naturally from where the conversation stopped.

============================================================
KNOWLEDGE BASE
============================================================

{context if context else "No relevant knowledge-base information was found."}

============================================================
PREVIOUS CONVERSATION
============================================================

{previous_chat}

============================================================
CURRENT QUESTION
============================================================

{query}

============================================================
ANSWER RULES
============================================================

1. Answer the current question naturally.

2. Use previous conversation when it helps understand the
   user's meaning.

3. Use the AJAY knowledge base when the question is about AJAY.

4. If relevant information is available in the knowledge base,
   answer confidently and naturally.

5. If the information is not available, do not make it up.

6. For questions unrelated to AJAY, you can answer normally
   using your general knowledge.

7. For casual conversation, do not unnecessarily mention
   the knowledge base.

8. Do not say things like:
   "According to my database..."
   unless the user specifically asks how you know.

9. Keep the conversation feeling human.

10. If the user asks something you genuinely cannot know,
    politely say that you don't have that information.

Now answer the current question.
"""


    # =====================================================
    # GEMINI
    # =====================================================

    try:

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

    except Exception as error:

        print("GEMINI ERROR:", repr(error))

        raise HTTPException(
            status_code=502,
            detail="AI service is temporarily unavailable.",
        )


    # =====================================================
    # RESPONSE
    # =====================================================

    answer = getattr(response, "text", None)

    if not answer:

        print("EMPTY GEMINI RESPONSE")

        raise HTTPException(
            status_code=502,
            detail="AI returned an empty response.",
        )

    answer = answer.strip()

    print("ANSWER:", answer)
    print("==============================\n")


    return {
        "answer": answer,
    }