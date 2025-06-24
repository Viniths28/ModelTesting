#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def create_address_data():
    print("➕ CREATING ADDRESS TEST DATA")
    print("=" * 50)
    
    with neo_client._driver.session() as session:
        result = session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            
            // Create Question node if it doesn't exist
            MERGE (q1:Question {questionId: "Q_AD_Residential_Address_(Customer-Current)"})
            ON CREATE SET q1.questionText = "What is your current residential address?"
            
            // Create test address datapoint
            MERGE (a)-[:SUPPLIES]->(d1:Datapoint {id: 'addr_' + a.applicantId})-[:ANSWERS]->(q1)
            ON CREATE SET d1.value = "123 Test Street, Melbourne VIC 3000", d1.createdAt = datetime()
            ON MATCH SET d1.value = "123 Test Street, Melbourne VIC 3000", d1.updatedAt = datetime()
            
            RETURN a.applicantId as applicant, d1.value as address
        """)
        
        record = result.single()
        if record:
            print(f"✅ Address data created for applicant: {record['applicant']}")
            print(f"   Address: {record['address']}")
        else:
            print("❌ Failed to create address data")
    
    print("\n🎯 EXPECTED FLOW BEHAVIOR:")
    print("   dealer_address_exists = True")
    print("   → Should show: Q_AD_Address_Check (verification question)")

if __name__ == "__main__":
    create_address_data() 