from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from neo4j import AsyncGraphDatabase
import os
from dotenv import load_dotenv
from app.services.address_history_handler import AddressHistoryHandler

load_dotenv()
router = APIRouter()

class AnswerPayload(BaseModel):
    applicant_id: str
    question_id: str
    value: str
    application_id: str

@router.post("/answer")
async def save_answer(payload: AnswerPayload):
    try:
        driver = AsyncGraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

        async with driver.session() as session:
            # First verify the question exists
            question_check = await session.run(
                """
                MATCH (q:Question {questionId: $questionId})
                RETURN q
                """,
                {"questionId": payload.question_id}
            )
            question = await question_check.single()
            if not question:
                raise HTTPException(status_code=404, detail=f"Question {payload.question_id} not found")

            # Create or update datapoint
            result = await session.run(
                """
                MERGE (a:Applicant {applicantId: $applicantId})
                MERGE (app:Application {applicationId: $applicationId})
                MERGE (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: $questionId})
                ON CREATE SET d.typedValue = $value, d.createdAt = datetime()
                ON MATCH SET d.typedValue = $value, d.updatedAt = datetime()
                RETURN d
                """,
                {
                    "applicantId": payload.applicant_id,
                    "applicationId": payload.application_id,
                    "questionId": payload.question_id,
                    "value": payload.value
                }
            )
            record = await result.single()
            if not record:
                raise HTTPException(status_code=500, detail="Failed to save answer")

            # Handle address history logic if applicable
            history_response = await AddressHistoryHandler.handle_address_history(
                driver,
                payload.applicant_id,
                payload.question_id,
                payload.value
            )

            response = {"message": "Answer saved successfully"}
            if history_response:
                response.update(history_response)

            return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await driver.close()