import os
from dotenv import load_dotenv

load_dotenv()

import uuid
import json
import logging
from fastapi import FastAPI, HTTPException, APIRouter, status, Depends, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from sqlmodel import SQLModel, create_engine

from app.schemas import ValidateRequest, ChatRequest
from agent_graph import app_graph

API_KEY = os.getenv("EMPLOYEE_API_KEY")
engine = create_engine("sqlite:///./employees.db")
SQLModel.metadata.create_all(engine)

def verify_api_key(x_api_key: str = Header(...)):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or missing API key"
        )

app = FastAPI(title="Agentic Employee Validator API")
router = APIRouter()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@router.get("/", name="health", operation_id="health_check")
async def health():
    return {"status": "ok", "message": "Agent server is alive"}

@router.post(
    "/validate",
    name="validate_employee",
    operation_id="validate_employee",
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_200_OK,
)
async def validate_employee(req: ValidateRequest):
    run_id = str(uuid.uuid4())
    user_prompt = f"Please process the following employee record: {req.payload.model_dump_json()}"
    try:
        initial_state = {"messages": [("user", user_prompt)]}
        final_state = app_graph.invoke(initial_state)
        final_answer = final_state["messages"][-1].content
        return {
            "run_id": run_id,
            "status": "ok",
            "agent_response": final_answer,
            "validated_data": jsonable_encoder(req.payload),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Error: {str(e)}")

@router.post(
    "/chat",
    name="chat_with_agent",
    operation_id="chat_with_agent",
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_200_OK,
)
async def chat_with_agent(req: ChatRequest):
    run_id = str(uuid.uuid4())
    
    formatted_history = []
    if req.history:
        for m in req.history:
            if m.get("role") in ["user", "assistant"]:
                formatted_history.append((m['role'], m['content']))

    initial_state = {
        "messages": formatted_history + [("user", req.message)]
    }

    # This generator function handles the streaming
    async def event_generator():
        try:
            final_answer = ""
            thought_steps = []  # <--- 1. Initialize a list to track thoughts
            
            for event in app_graph.stream(initial_state):
                for node_name, output in event.items():
                    step_info = {"type": "step", "node": node_name}
                    detail_text = "" # Track the text for the summary
                    
                    if node_name == "tools":
                        tool_calls = []
                        for msg in output.get("messages", []):
                            if hasattr(msg, 'content'):
                                detail_text = f"🛠️ Tool executed: {msg.content[:100]}..."
                    elif node_name == "agent":
                        last_msg = output.get("messages", [])[-1]
                        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                            tool_names = [tc['name'] for tc in last_msg.tool_calls]
                            detail_text = f"🧠 Thinking... calling tools: {', '.join(tool_names)}"
                        else:
                            detail_text = "✅ Finalizing response..."
                            final_answer = last_msg.content
                    
                    if detail_text:
                        step_info["detail"] = detail_text
                        thought_steps.append(detail_text) # <--- 2. Store the step
                    
                    yield json.dumps(step_info) + "\n"
            
            # 3. Include the joined thought process in the final event
            yield json.dumps({
                "type": "final", 
                "answer": final_answer, 
                "thought": "\n".join(thought_steps) 
            }) + "\n"
            
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)