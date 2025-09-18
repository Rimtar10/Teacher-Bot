from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import httpx
import asyncio

load_dotenv()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

app = FastAPI(title="Teacher Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in file")

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

async def get_mistral_response(user_message: str) -> str:
    """Get response from Mistral API with teacher persona"""
    

    system_prompt = """You're a private tutor for students of all ages and levels.
    i want you to answer each question asked by the user in a way that is educational and encourages learning.
    add examples to all your answers. and let your answers be detailed and based on real recources.
    if the user asks a question that is not related to learning or education, politely steer the conversation back to educational topics.
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    payload = {
        "model": "mistral-large-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "top_p": 1,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(MISTRAL_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e}")
        return "I'm having trouble connecting to my knowledge base right now. Could you please try again?"
    except httpx.RequestError as e:
        print(f"Request Error: {e}")
        return "I'm experiencing some technical difficulties. Please try again in a moment."
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "I apologize, but I'm having some technical issues right now. Please try again."

def get_fallback_response(user_message: str) -> str:
    """Fallback response when API is unavailable"""
    message = user_message.lower()
    
    if any(greeting in message for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return "Hello! I'm your teacher assistant. How can I help you learn something new today?"
    elif any(word in message for word in ["help", "explain", "what", "how", "why"]):
        return "I'd love to help you understand that better! Could you be more specific about what you'd like to learn?"
    elif any(word in message for word in ["thank", "thanks"]):
        return "You're very welcome! Keep up the great work with your learning!"
    else:
        return "That's an interesting question! I'm here to help you learn. Could you tell me more about what you'd like to understand?"

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint that uses Mistral API for responses"""
    try:

        reply = await get_mistral_response(request.message)
        return ChatResponse(reply=reply)
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        reply = get_fallback_response(request.message)
        return ChatResponse(reply=reply)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Teacher Chatbot API is running!"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "api_key_configured": bool(MISTRAL_API_KEY)}
