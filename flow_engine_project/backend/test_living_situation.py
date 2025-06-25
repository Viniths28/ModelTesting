#!/usr/bin/env python3

import sys
import os
import uuid
from typing import Any, Dict

# Ensure the backend directory is in the Python path
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.traversal import walk_section
from flow_engine.neo import neo_client

# --- Test Configuration ---
TEST_APPLICANT_ID = "test_applicant_living_situation"
TEST_APPLICATION_ID = "test_app_living_situation"
TEST_SECTION_ID = "SEC_LIVING_SITUATION" # Assuming this is the section ID

# --- Helper Functions ---

def run_cypher(query: str, params: Dict[str, Any] = None):
    """A simple wrapper to execute Cypher queries."""
    if params is None:
        params = {}
    with neo_client._driver.session() as session:
        result = session.run(query, **params)
        return [record.data() for record in result]

def cleanup_test_data():
    """Remove all data associated with the test applicant."""
    print("--- Cleaning up previous test data ---")
    run_cypher(
        "MATCH (a:Applicant {applicantId: $app_id}) DETACH DELETE a",
        {"app_id": TEST_APPLICANT_ID}
    )
    # Also delete AddressHistory nodes if they got orphaned somehow
    run_cypher(
        "MATCH (a:Applicant {applicantId: $app_id})-[:HAS_HISTORY]->(h:AddressHistory) DETACH DELETE h",
        {"app_id": TEST_APPLICANT_ID}
    )

def create_test_applicant():
    """Create the test applicant node."""
    print("--- Creating test applicant ---")
    run_cypher(
        "CREATE (a:Applicant {applicantId: $app_id, applicationId: $app_id})",
        {"app_id": TEST_APPLICANT_ID}
    )

def answer_question(question_id: str, value: str):
    """Simulate a user answering a question by creating a Datapoint."""
    print(f"✍️  ANSWERING: '{question_id}' with value '{value}'")
    # For prior addresses, we need to link the datapoint to the AddressHistory node
    if "Prior" in question_id:
        query = """
        MATCH (a:Applicant {applicantId: $app_id})
        MATCH (a)-[:HAS_HISTORY]->(h:AddressHistory)
        CREATE (dp:Datapoint {datapointId: $dp_id, value: $value})
        CREATE (dp)-[:ANSWERS]->(:Question {questionId: $q_id})
        CREATE (h)-[:HAS_DATAPOINT]->(dp) // This links prior answers to the history node
        """
    else:
        query = """
        MATCH (a:Applicant {applicantId: $app_id})
        CREATE (dp:Datapoint {datapointId: $dp_id, value: $value})
        CREATE (dp)-[:ANSWERS]->(:Question {questionId: $q_id})
        CREATE (a)-[:SUPPLIES]->(dp)
        """
    params = {
        "app_id": TEST_APPLICANT_ID,
        "q_id": question_id,
        "value": value,
        "dp_id": str(uuid.uuid4())
    }
    run_cypher(query, params)
    print("----------------------------------------")

def run_engine_step(step_name: str):
    """Call the flow engine and print the result."""
    print(f"▶️  RUNNING ENGINE: {step_name}")
    context = {
        "applicantId": TEST_APPLICANT_ID,
        "applicationId": TEST_APPLICATION_ID,
    }
    result = walk_section(TEST_SECTION_ID, context)
    
    next_question = result.get("question")
    if next_question:
        print(f"✅ Engine returned next question: {next_question['questionId']}")
    else:
        print("✅ Engine reported flow is complete for now.")
    
    print(f"   - Variables resolved:")
    for var, data in result.get("vars", {}).items():
        if 'duration' in var or 'count' in var:
             print(f"     - {var}: {data.get('value')}")

    return next_question

def test_living_situation_flow():
    """Execute the full test case for the living situation loop."""
    try:
        cleanup_test_data()
        create_test_applicant()

        # --- STEP 1: Start the flow ---
        next_q = run_engine_step("Step 1 - Initial call")
        assert next_q['questionId'] == 'Q_AD_Residential_Status_(Customer)', "Flow should start with status question"
        answer_question(next_q['questionId'], "Renting")

        # --- STEP 2: Answer status, should get current duration ---
        next_q = run_engine_step("Step 2 - After answering status")
        assert next_q['questionId'] == 'Q_AD_Residential_Start_Date_(Customer)', "Should ask for current duration"
        answer_question(next_q['questionId'], "1") # DURATION < 3 MONTHS

        # --- STEP 3: LOOP 1 START - Should ask for Prior Address ---
        next_q = run_engine_step("Step 3 - Loop 1, Need Address")
        assert next_q['questionId'] == 'Q_AD_Residential_Address_(Customer-Prior)', "Should ask for prior address"
        answer_question(next_q['questionId'], "123 Old Street")

        # --- STEP 4: LOOP 1 - Should ask for Prior Date ---
        next_q = run_engine_step("Step 4 - Loop 1, Need Date")
        assert next_q['questionId'] == 'Q_AD_Residential_Start_Date(Customer_Prior)', "Should ask for prior start date"
        answer_question(next_q['questionId'], "1.5") # Total duration is now 1 + 1.5 = 2.5

        # --- STEP 5: LOOP 2 START - Should ask for Prior Address AGAIN ---
        next_q = run_engine_step("Step 5 - Loop 2, Need Address")
        assert next_q['questionId'] == 'Q_AD_Residential_Address_(Customer-Prior)', "Should ask for prior address AGAIN"
        answer_question(next_q['questionId'], "456 Past Lane")

        # --- STEP 6: LOOP 2 - Should ask for Prior Date AGAIN ---
        next_q = run_engine_step("Step 6 - Loop 2, Need Date")
        assert next_q['questionId'] == 'Q_AD_Residential_Start_Date(Customer_Prior)', "Should ask for prior start date AGAIN"
        answer_question(next_q['questionId'], "1") # Total duration is now 2.5 + 1 = 3.5

        # --- STEP 7: EXIT LOOP - Duration is >= 3, should ask about lease ---
        next_q = run_engine_step("Step 7 - Exit Loop")
        assert next_q['questionId'] == 'Q_AD_Individuals_on_Lease', "Should exit loop and ask about lease"
        answer_question(next_q['questionId'], "2")

        # --- STEP 8: COMPLETE ---
        next_q = run_engine_step("Step 8 - Final Completion")
        assert next_q is None, "Flow should be complete"

        print("\n🎉🎉🎉 LIVING SITUATION FLOW TEST PASSED! 🎉🎉🎉")

    except Exception as e:
        print(f"\n❌❌❌ TEST FAILED: {e} ❌❌❌")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    test_living_situation_flow() 