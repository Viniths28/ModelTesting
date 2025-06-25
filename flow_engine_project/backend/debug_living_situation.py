#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def run_cypher(query: str, params: dict = None):
    """Execute a Cypher query and return results."""
    if params is None:
        params = {}
    with neo_client._driver.session() as session:
        result = session.run(query, **params)
        return [record.data() for record in result]

def debug_living_situation():
    """Debug the living situation flow setup."""
    
    applicant_id = "App001"  # Your test applicant
    
    print("🔍 DEBUGGING LIVING SITUATION FLOW")
    print("=" * 50)
    
    # Check if applicant exists
    applicant_check = run_cypher(
        "MATCH (a:Applicant {applicantId: $app_id}) RETURN a",
        {"app_id": applicant_id}
    )
    print(f"1. Applicant exists: {len(applicant_check) > 0}")
    
    # Check current address duration answer
    current_duration = run_cypher(
        """
        MATCH (a:Applicant {applicantId: $app_id})-[:SUPPLIES]->(dp:Datapoint)-[:ANSWERS]->(:Question {questionId: 'Q_AD_Residential_Start_Date_(Customer)'})
        RETURN dp.value as duration
        """,
        {"app_id": applicant_id}
    )
    print(f"2. Current duration answer: {current_duration}")
    
    # Check if AddressHistory node exists
    history_check = run_cypher(
        """
        MATCH (a:Applicant {applicantId: $app_id})-[:HAS_HISTORY]->(h:AddressHistory)
        RETURN h
        """,
        {"app_id": applicant_id}
    )
    print(f"3. AddressHistory node exists: {len(history_check) > 0}")
    
    # Test the CreateNode action manually
    print("\n4. Testing CreateNode action manually...")
    try:
        result = run_cypher(
            "MATCH (a:Applicant {applicantId: $app_id}) MERGE (a)-[:HAS_HISTORY]->(h:AddressHistory) RETURN h",
            {"app_id": applicant_id}
        )
        print(f"   ✅ CreateNode action works: {len(result) > 0}")
    except Exception as e:
        print(f"   ❌ CreateNode action failed: {e}")
    
    # Check the section structure
    print("\n5. Checking section edges...")
    section_edges = run_cypher(
        """
        MATCH (s:Section {sectionId: 'SEC_1a879403-51e3-4eef-b6c5-00a613f8f76e'})-[e]->(target)
        RETURN type(e) as edge_type, target.questionId as target_question, e.askWhen as condition
        ORDER BY e.orderInForm, id(e)
        """
    )
    for edge in section_edges:
        print(f"   - {edge['edge_type']} → {edge['target_question']} | askWhen: {edge['condition']}")
    
    # Check edges from the current duration question
    print("\n6. Checking edges from Q_AD_Residential_Start_Date_(Customer)...")
    duration_edges = run_cypher(
        """
        MATCH (q:Question {questionId: 'Q_AD_Residential_Start_Date_(Customer)'})-[e]->(target)
        RETURN type(e) as edge_type, 
               CASE 
                 WHEN 'Question' IN labels(target) THEN target.questionId 
                 WHEN 'actionType' IN keys(target) THEN target.actionType 
                 ELSE 'Unknown' 
               END as target_info,
               e.askWhen as condition
        ORDER BY e.orderInForm, id(e)
        """
    )
    for edge in duration_edges:
        print(f"   - {edge['edge_type']} → {edge['target_info']} | askWhen: {edge['condition']}")
    
    print("\n" + "=" * 50)
    print("Debug complete!")

if __name__ == "__main__":
    debug_living_situation() 