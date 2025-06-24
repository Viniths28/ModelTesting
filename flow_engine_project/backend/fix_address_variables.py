#!/usr/bin/env python3

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def fix_address_section():
    print("🔧 FIXING ADDRESS SECTION VARIABLES & DATA")
    print("=" * 60)
    
    section_id = "SEC_1a879403-51e3-4eef-b6c5-00a613f8f76e"
    
    # Fixed variable definitions
    fixed_variables = [
        {
            "name": "dealer_address_exists",
            "cypher": """
                MATCH (a:Applicant {applicantId:$applicantId})
                OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId:"Q_AD_Residential_Address_(Customer-Current)"})
                RETURN COUNT(d) > 0 AS value
            """
        },
        {
            "name": "current_applicant", 
            "cypher": "MATCH (a:Applicant {applicantId:$applicantId}) RETURN elementId(a) AS value"
        },
        {
            "name": "current_address_dp",
            "cypher": """
                MATCH (a:Applicant {applicantId:$applicantId})-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId:"Q_AD_Residential_Address_(Customer-Current)"})
                RETURN d
            """
        },
        {
            "name": "address_verification_answer",
            "cypher": """
                MATCH (a:Applicant {applicantId:$applicantId})
                OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId:"Q_AD_Address_Check"})
                RETURN COALESCE(d.value, '') AS value
            """
        },
        {
            "name": "current_duration",
            "cypher": """
                MATCH (a:Applicant {applicantId:$applicantId})
                OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId:"Q_AD_Residential_Start_Date_(Customer)"})
                WHERE d.value IS NOT NULL
                RETURN COALESCE(duration.between(datetime(d.value), datetime()).months, 0) AS value
            """
        },
        {
            "name": "total_duration",
            "cypher": """
                MATCH (a:Applicant {applicantId:$applicantId})
                OPTIONAL MATCH (a)-[:SUPPLIES]->(dCurrent:Datapoint)-[:ANSWERS]->(q:Question {questionId:"Q_AD_Residential_Start_Date_(Customer)"})
                WITH a, COALESCE(duration.between(datetime(dCurrent.value), datetime()).months, 0) as current_months
                OPTIONAL MATCH (a)-[:HAS_ADDRESS_HISTORY]->(ah)-[:SUPPLIES]->(dPrior:Datapoint)-[:ANSWERS]->(q2:Question {questionId:"Q_AD_Residential_Start_Date_(CustomerPrior)"})
                WITH current_months, sum(COALESCE(duration.between(datetime(dPrior.value), datetime()).months, 0)) as prior_months
                RETURN current_months + COALESCE(prior_months, 0) AS value
            """
        }
    ]
    
    # Step 1: Update section variables
    print("1. Updating section variables...")
    with neo_client._driver.session() as session:
        session.run("""
            MATCH (s:Section {sectionId: $sectionId})
            SET s.variables = $variables
        """, sectionId=section_id, variables=json.dumps(fixed_variables))
    
    print("✅ Variables updated")
    
    # Step 2: Create some test data to make the flow work
    print("\n2. Creating test data...")
    
    with neo_client._driver.session() as session:
        # Create test address data for the applicant
        session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            
            // Create Question nodes if they don't exist
            MERGE (q1:Question {questionId: "Q_AD_Residential_Address_(Customer-Current)"})
            ON CREATE SET q1.questionText = "What is your current residential address?"
            
            MERGE (q2:Question {questionId: "Q_AD_Address_Check"})
            ON CREATE SET q2.questionText = "Is this your correct address?"
            
            MERGE (q3:Question {questionId: "Q_AD_Residential_Start_Date_(Customer)"})
            ON CREATE SET q3.questionText = "When did you start living at this address?"
            
            // Create test address datapoint
            MERGE (a)-[:SUPPLIES]->(d1:Datapoint {id: 'addr_' + a.applicantId})-[:ANSWERS]->(q1)
            ON CREATE SET d1.value = "123 Test Street, Melbourne VIC 3000", d1.createdAt = datetime()
            
            // Create test start date datapoint (1 year ago)
            MERGE (a)-[:SUPPLIES]->(d3:Datapoint {id: 'start_' + a.applicantId})-[:ANSWERS]->(q3)
            ON CREATE SET d3.value = toString(datetime() - duration({months: 12})), d3.createdAt = datetime()
            
            RETURN a.applicantId as applicant, count(*) as datapoints_created
        """)
    
    print("✅ Test data created")
    
    # Step 3: Test the variables
    print("\n3. Testing fixed variables...")
    from flow_engine.traversal import _load_section_vars, Context
    
    ctx_dict = {
        'applicationId': 'Appl_123',
        'applicantId': 'App001',
        'sectionId': section_id,
        'isPrimaryFlow': True
    }
    
    var_defs = _load_section_vars(section_id)
    ctx = Context(input_params=ctx_dict, var_defs=var_defs)
    
    for var_name in ['dealer_address_exists', 'current_applicant']:
        try:
            value = ctx.resolve_var(var_name)
            print(f"  {var_name}: {value} (type: {type(value).__name__})")
        except Exception as e:
            print(f"  {var_name}: ERROR - {e}")
    
    print("\n4. Testing flow execution...")
    from flow_engine.traversal import walk_section
    
    try:
        result = walk_section(section_id, ctx_dict)
        print("✅ Flow execution succeeded!")
        print(f"Result: completed={result.get('completed')}, question={result.get('question', {}).get('questionId') if result.get('question') else None}")
        
        if result.get('question'):
            print(f"Next question: {result['question']['questionId']}")
        elif result.get('completed'):
            print("⚠️  Section completed immediately - check edge conditions")
            
    except Exception as e:
        print(f"❌ Flow execution failed: {e}")

if __name__ == "__main__":
    fix_address_section() 