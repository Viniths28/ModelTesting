from fastapi import APIRouter, Request
from pydantic import BaseModel
from neo4j import AsyncGraphDatabase
import os

router = APIRouter()

class SeedPayload(BaseModel):
    application_id: str
    applicant_id: str
    dealer_data: dict

@router.post("/seed")
async def seed_graph(payload: SeedPayload):
    driver = AsyncGraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))
    created_nodes = []
    async with driver.session() as session:
        # First create Application and Applicant nodes
        await session.run(
            """
            MERGE (app:Application {applicationId: $applicationId})
            MERGE (a:Applicant {applicantId: $applicantId})
            MERGE (app)-[:HAS_APPLICANT]->(a)
            """,
            {
                "applicationId": payload.application_id,
                "applicantId": payload.applicant_id
            }
        )
        
        # Then create Datapoints for each dealer data item
        for qid, value in payload.dealer_data.items():
            result = await session.run(
                """
                MATCH (q:Question {questionId: $questionId})
                MATCH (a:Applicant {applicantId: $applicantId})
                CREATE (dp:Datapoint {
                    datapointId: randomUUID(),
                    typedValue: $value,
                    createdAt: datetime()
                })
                MERGE (a)-[:SUPPLIES]->(dp)
                MERGE (dp)-[:ANSWERS]->(q)
                RETURN dp.datapointId as datapointId
                """,
                {"questionId": qid, "applicantId": payload.applicant_id, "value": value}
            )
            record = await result.single()
            if record:
                created_nodes.append({
                    "question_id": qid,
                    "datapoint_id": record["datapointId"],
                    "value": value
                })
    
    return {
        "status": "success",
        "message": "Seed data ingested successfully",
        "created": {
            "application_id": payload.application_id,
            "applicant_id": payload.applicant_id,
            "datapoints": created_nodes
        }
    }