from fastapi import FastAPI
from app.routes import seed, next_question, answer, trigger_action

app = FastAPI(
    title="Graph-Based Loan Application API",
    description="Handles dynamic questionnaire flows using Neo4j",
    version="1.0.0"
)

# Include route modules
app.include_router(seed.router, prefix="/api/v1/graph", tags=["Seed"])
app.include_router(next_question.router, prefix="/api/v1/graph", tags=["Next Question"])
app.include_router(answer.router, prefix="/api/v1/graph", tags=["Answer"])
app.include_router(trigger_action.router, prefix="/api/v1/graph", tags=["Action Trigger"])
