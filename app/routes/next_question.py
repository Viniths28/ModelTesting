from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from neo4j import AsyncGraphDatabase
import os
from dotenv import load_dotenv
from app.services.section_handlers import SectionHandlerFactory

load_dotenv()
router = APIRouter()

class NextQuestionPayload(BaseModel):
    section_id: str
    applicant_id: str
    application_id: str
    current_question_id: str | None = None

@router.post("/next-question")
async def get_next_question(payload: NextQuestionPayload):
    try:
        driver = AsyncGraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

        # Get the appropriate handler for the section
        handler = SectionHandlerFactory.get_handler(payload.section_id)
        
        # Get next question using the handler
        question = await handler.get_next_question(
            payload.section_id,
            payload.applicant_id,
            payload.application_id,
            driver
        )

        if question:
            return question
        return {"message": "No more questions"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await driver.close()
