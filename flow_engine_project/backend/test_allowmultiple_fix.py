#!/usr/bin/env python3

import sys
import os
import uuid
from typing import Any, Dict
import json

# Ensure the backend directory is in the Python path
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.traversal import walk_section
from flow_engine.neo import neo_client

# --- Test Configuration ---
TEST_APPLICANT_ID = "test_allowmultiple_fix"
TEST_APPLICATION_ID = "test_app_allowmultiple"
TEST_SECTION_ID = "SEC_ALLOWMULTIPLE_TEST"

def run_cypher(query: str, params: Dict[str, Any] = None):
    """A simple wrapper to execute Cypher queries."""
    if params is None:
        params = {}
    with neo_client._driver.session() as session:
        result = session.run(query, **params)
        return [record.data() for record in result]

def cleanup_test_data():
    """Remove all test data."""
    print("🧹 Cleaning up test data...")
    
    # Clean up test nodes and relationships
    run_cypher("""
        MATCH (n) WHERE 
            n.sectionId = $sec_id OR 
            n.applicantId = $app_id OR
            n.questionId STARTS WITH 'Q_TEST_' OR
            n.actionId STARTS WITH 'A_TEST_'
        DETACH DELETE n
    """, {"sec_id": TEST_SECTION_ID, "app_id": TEST_APPLICANT_ID})

def create_test_flow():
    """Create a simple test flow with allowMultiple question and loop condition."""
    print("🏗️ Creating test flow structure...")
    
    # Create section with variables
    section_variables = [
        {
            "name": "address_count",
            "cypher": "MATCH (a:Applicant {applicantId: $applicantId})-[:HAS_HISTORY_PROPERTY]->(h:AddressHistory)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: 'Q_TEST_Address'}) RETURN count(d) as count"
        },
        {
            "name": "should_continue_loop", 
            "cypher": "MATCH (a:Applicant {applicantId: $applicantId})-[:HAS_HISTORY_PROPERTY]->(h:AddressHistory)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: 'Q_TEST_Address'}) WITH count(d) as address_count RETURN CASE WHEN address_count < 3 THEN true ELSE false END as result"
        },
        {
            "name": "address_history_node",
            "cypher": "MATCH (a:Applicant {applicantId: $applicantId})-[:HAS_HISTORY_PROPERTY]->(h:AddressHistory) RETURN h"
        }
    ]
    
    # Create section - use proper JSON formatting
    run_cypher("""
        CREATE (s:Section {
            sectionId: $sec_id,
            variables: $vars,
            sourceNode: "cypher: MATCH (a:Applicant {applicantId: $applicantId}) RETURN a"
        })
    """, {
        "sec_id": TEST_SECTION_ID,
        "vars": json.dumps(section_variables)  # Proper JSON encoding
    })
    
    # Create questions
    run_cypher("""
        CREATE (q1:Question {questionId: 'Q_TEST_Address', allowMultiple: true, text: 'Enter an address'})
        CREATE (q2:Question {questionId: 'Q_TEST_Complete', text: 'Flow complete - any final info?'})
    """)
    
    # Create action to create AddressHistory
    run_cypher("""
        CREATE (a1:Action {
            actionId: 'A_TEST_CreateHistory',
            actionType: 'CreateNode',
            returnImmediately: false,
            cypher: 'MATCH (applicant:Applicant {applicantId: $applicantId}) MERGE (applicant)-[:HAS_HISTORY_PROPERTY]->(h:AddressHistory) RETURN elementId(h)'
        })
    """)
    
    # Get node IDs for relationships
    section_id = run_cypher("MATCH (s:Section {sectionId: $sec_id}) RETURN id(s) as id", {"sec_id": TEST_SECTION_ID})[0]["id"]
    q1_id = run_cypher("MATCH (q:Question {questionId: 'Q_TEST_Address'}) RETURN id(q) as id")[0]["id"]
    q2_id = run_cypher("MATCH (q:Question {questionId: 'Q_TEST_Complete'}) RETURN id(q) as id")[0]["id"]
    a1_id = run_cypher("MATCH (a:Action {actionId: 'A_TEST_CreateHistory'}) RETURN id(a) as id")[0]["id"]
    
    # Create flow relationships
    # Section -> Action (create history)
    run_cypher("""
        MATCH (s:Section), (a:Action)
        WHERE id(s) = $s_id AND id(a) = $a_id
        CREATE (s)-[:PRECEDES {orderInForm: 1}]->(a)
    """, {"s_id": section_id, "a_id": a1_id})
    
    # Action -> Question (ask for address if should continue)
    run_cypher("""
        MATCH (a:Action), (q:Question)
        WHERE id(a) = $a_id AND id(q) = $q_id
        CREATE (a)-[:PRECEDES {
            orderInForm: 1,
            askWhen: "{{ should_continue_loop }} == True",
            sourceNode: "{{ address_history_node }}"
        }]->(q)
    """, {"a_id": a1_id, "q_id": q1_id})
    
    # Action -> Complete Question (if loop should exit)
    run_cypher("""
        MATCH (a:Action), (q:Question)
        WHERE id(a) = $a_id AND id(q) = $q_id
        CREATE (a)-[:PRECEDES {
            orderInForm: 2,
            askWhen: "{{ should_continue_loop }} == False"
        }]->(q)
    """, {"a_id": a1_id, "q_id": q2_id})
    
    # Address Question -> Action (loop back to action for next iteration)
    run_cypher("""
        MATCH (q:Question), (a:Action)
        WHERE id(q) = $q_id AND id(a) = $a_id
        CREATE (q)-[:PRECEDES {orderInForm: 1}]->(a)
    """, {"q_id": q1_id, "a_id": a1_id})

def create_test_applicant():
    """Create test applicant."""
    print("👤 Creating test applicant...")
    run_cypher("""
        CREATE (a:Applicant {applicantId: $app_id, applicationId: $app_id})
    """, {"app_id": TEST_APPLICANT_ID})

def answer_question(question_id: str, value: str):
    """Answer a question by creating appropriate datapoint."""
    print(f"✍️ Answering '{question_id}' with value '{value}'")
    
    # For allowMultiple questions, link to AddressHistory
    if question_id == 'Q_TEST_Address':
        run_cypher("""
            MATCH (a:Applicant {applicantId: $app_id})-[:HAS_HISTORY_PROPERTY]->(h:AddressHistory)
            MATCH (q:Question {questionId: $q_id})
            CREATE (dp:Datapoint {datapointId: $dp_id, value: $value})
            CREATE (dp)-[:ANSWERS]->(q)
            CREATE (h)-[:SUPPLIES]->(dp)
        """, {
            "app_id": TEST_APPLICANT_ID,
            "q_id": question_id,
            "value": value,
            "dp_id": str(uuid.uuid4())
        })
    else:
        # Regular questions link to Applicant
        run_cypher("""
            MATCH (a:Applicant {applicantId: $app_id})
            MATCH (q:Question {questionId: $q_id})
            CREATE (dp:Datapoint {datapointId: $dp_id, value: $value})
            CREATE (dp)-[:ANSWERS]->(q)
            CREATE (a)-[:SUPPLIES]->(dp)
        """, {
            "app_id": TEST_APPLICANT_ID,
            "q_id": question_id,
            "value": value,
            "dp_id": str(uuid.uuid4())
        })

def run_engine_step(step_name: str):
    """Run the engine and return the result."""
    print(f"\n▶️ Running Engine: {step_name}")
    context = {
        "applicantId": TEST_APPLICANT_ID,
        "applicationId": TEST_APPLICATION_ID,
    }
    
    result = walk_section(TEST_SECTION_ID, context)
    
    next_question = result.get("question")
    if next_question:
        print(f"✅ Next question: {next_question['questionId']}")
    else:
        print("✅ Flow completed")
    
    # Print relevant variables
    vars_data = result.get("vars", {})
    print(f"   📊 Available variables: {list(vars_data.keys())}")
    for var_name in ["address_count", "should_continue_loop"]:
        if var_name in vars_data:
            print(f"   📊 {var_name}: {vars_data[var_name].get('value')}")
    
    return next_question

def test_allowmultiple_fix():
    """Test the allowMultiple fix with a looping scenario."""
    try:
        cleanup_test_data()
        create_test_flow()
        create_test_applicant()
        
        print("\n" + "="*60)
        print("🧪 TESTING ALLOWMULTIPLE FIX")
        print("="*60)
        
        # Step 1: Initial call - should create AddressHistory and ask for first address
        next_q = run_engine_step("Step 1 - Initial call")
        assert next_q and next_q['questionId'] == 'Q_TEST_Address', f"Expected Q_TEST_Address, got {next_q}"
        
        # Answer first address
        answer_question('Q_TEST_Address', '123 First Street')
        
        # Step 2: Should loop back and ask for second address (address_count=1, should_continue=true)
        next_q = run_engine_step("Step 2 - After first address")
        assert next_q and next_q['questionId'] == 'Q_TEST_Address', f"Expected Q_TEST_Address again, got {next_q}"
        
        # Answer second address
        answer_question('Q_TEST_Address', '456 Second Avenue')
        
        # Step 3: Should loop back and ask for third address (address_count=2, should_continue=true)
        next_q = run_engine_step("Step 3 - After second address")
        assert next_q and next_q['questionId'] == 'Q_TEST_Address', f"Expected Q_TEST_Address again, got {next_q}"
        
        # Answer third address
        answer_question('Q_TEST_Address', '789 Third Road')
        
        # Step 4: Should exit loop and ask completion question (address_count=3, should_continue=false)
        next_q = run_engine_step("Step 4 - After third address")
        assert next_q and next_q['questionId'] == 'Q_TEST_Complete', f"Expected Q_TEST_Complete, got {next_q}"
        
        # Answer completion question
        answer_question('Q_TEST_Complete', 'All done!')
        
        # Step 5: Should be complete
        next_q = run_engine_step("Step 5 - Final")
        assert next_q is None, f"Expected flow to be complete, got {next_q}"
        
        print("\n" + "="*60)
        print("🎉 ALLOWMULTIPLE FIX TEST PASSED!")
        print("✅ Loop correctly executed 3 iterations")
        print("✅ allowMultiple question asked multiple times against same container")
        print("✅ Edge conditions controlled loop exit properly")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    test_allowmultiple_fix() 