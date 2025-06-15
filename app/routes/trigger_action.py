# app/routes/trigger_action.py

from fastapi import APIRouter
from pydantic import BaseModel
from app.graph_driver import get_driver
import uuid
from datetime import datetime

router = APIRouter()

class TriggerActionRequest(BaseModel):
    action_id: str
    application_id: str
    applicant_id: str

@router.post("/")
def trigger_action(payload: TriggerActionRequest):
    query = """
    MATCH (a:Action {actionId: $action_id})
    RETURN a.actionType AS actionType, a.parameters AS parameters
    """

    with get_driver().session() as session:
        record = session.run(query, {
            "action_id": payload.action_id
        }).single()

    if not record:
        return {"message": "Action not found"}

    action_type = record["actionType"]
    params = record["parameters"]

    # ==== Perform Logic ====
    if action_type == "create_node":
        node_type = params.get("nodeType")
        new_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with get_driver().session() as session:
            if node_type == "Applicant":
                session.run("""
                MATCH (app:Application {id: $application_id})
                CREATE (coapp:Applicant {
                    id: $new_id,
                    role: 'co-applicant',
                    createdAt: $created_at
                })
                CREATE (app)-[:HAS_APPLICANT]->(coapp)
                """, {
                    "application_id": payload.application_id,
                    "new_id": new_id,
                    "created_at": now
                })
                return {"message": "Co-applicant created", "new_applicant_id": new_id}

    elif action_type == "go_to_section":
        return {
            "message": "Navigate to section",
            "target_section": params.get("targetSection")
        }

    elif action_type == "complete_section":
        # For now, just a mock example
        return {
            "message": f"Section marked complete",
            "sectionId": params.get("targetSectionId")
        }

    return {"message": "Action executed", "type": action_type}
