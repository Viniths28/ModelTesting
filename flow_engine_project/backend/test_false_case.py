#!/usr/bin/env python3

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client
from flow_engine.traversal import walk_section, Context, _load_section_vars

def test_false_case():
    print("🧪 TESTING FALSE CASE - No Address Data")
    print("=" * 60)
    
    section_id = "SEC_1a879403-51e3-4eef-b6c5-00a613f8f76e"
    ctx_dict = {
        'applicationId': 'Appl_123',
        'applicantId': 'App001',
        'sectionId': section_id,
        'isPrimaryFlow': True
    }
    
    # Step 1: Remove test address data temporarily
    print("1. Removing test address data...")
    with neo_client._driver.session() as session:
        result = session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: "Q_AD_Residential_Address_(Customer-Current)"})
            WITH d, count(*) as datapoints_found
            FOREACH (dp IN CASE WHEN d IS NOT NULL THEN [d] ELSE [] END |
                DETACH DELETE dp
            )
            RETURN datapoints_found
        """)
        
        record = result.single()
        if record:
            print(f"   Removed {record['datapoints_found']} address datapoints")
        else:
            print("   No address datapoints found to remove")
    
    # Step 2: Test dealer_address_exists variable
    print("\n2. Testing dealer_address_exists variable...")
    var_defs = _load_section_vars(section_id)
    ctx = Context(input_params=ctx_dict, var_defs=var_defs)
    
    dealer_exists = ctx.resolve_var('dealer_address_exists')
    print(f"   dealer_address_exists: {dealer_exists} (type: {type(dealer_exists).__name__})")
    
    if dealer_exists is False:
        print("   ✅ Variable correctly returns False")
    else:
        print(f"   ❌ Expected False, got {dealer_exists}")
    
    # Step 3: Test flow execution
    print("\n3. Testing flow execution...")
    try:
        result = walk_section(section_id, ctx_dict)
        print("✅ Flow execution succeeded!")
        
        if result.get('question'):
            question_id = result['question']['questionId']
            print(f"   Next question: {question_id}")
            
            if question_id == "Q_AD_Residential_Address_(Customer-Current)":
                print("   ✅ Correctly shows address collection question!")
            else:
                print(f"   ❌ Expected address collection question, got {question_id}")
        elif result.get('completed'):
            print("   ❌ Section completed immediately - should have shown address collection question")
        else:
            print(f"   ❌ Unexpected result: {result}")
            
    except Exception as e:
        print(f"❌ Flow execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Show what edge condition was evaluated
    print(f"\n4. Edge conditions evaluation:")
    print(f"   dealer_address_exists == True: {dealer_exists == True}")
    print(f"   dealer_address_exists == False: {dealer_exists == False}")

def restore_test_data():
    print("\n" + "=" * 60)
    print("🔄 RESTORING TEST DATA")
    print("=" * 60)
    
    with neo_client._driver.session() as session:
        session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            
            // Create Question node if it doesn't exist
            MERGE (q1:Question {questionId: "Q_AD_Residential_Address_(Customer-Current)"})
            ON CREATE SET q1.questionText = "What is your current residential address?"
            
            // Recreate test address datapoint
            MERGE (a)-[:SUPPLIES]->(d1:Datapoint {id: 'addr_' + a.applicantId})-[:ANSWERS]->(q1)
            ON CREATE SET d1.value = "123 Test Street, Melbourne VIC 3000", d1.createdAt = datetime()
            
            RETURN count(*) as restored
        """)
    
    print("✅ Test data restored")

if __name__ == "__main__":
    test_false_case()
    
    # Ask user if they want to restore test data
    print("\n" + "=" * 60)
    response = input("Restore test data? (y/n): ").lower().strip()
    if response in ['y', 'yes']:
        restore_test_data()
    else:
        print("Test data left removed. Run fix_address_variables.py to restore if needed.") 