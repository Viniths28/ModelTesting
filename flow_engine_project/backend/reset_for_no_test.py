#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def reset_for_no_test():
    print("🔄 RESETTING FOR 'NO' ANSWER TEST")
    print("=" * 50)
    
    with neo_client._driver.session() as session:
        # Delete the address verification answer
        session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: "Q_AD_Address_Check"})
            FOREACH (dp IN CASE WHEN d IS NOT NULL THEN [d] ELSE [] END | DETACH DELETE dp)
            RETURN count(*) as deleted_verification
        """)
        
        # Also delete the address collection answer so engine will ask for it
        session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: "Q_AD_Residential_Address_(Customer-Current)"})
            FOREACH (dp IN CASE WHEN d IS NOT NULL THEN [d] ELSE [] END | DETACH DELETE dp)
            RETURN count(*) as deleted_address
        """)
        
        print("✅ Deleted address verification answer")
        print("✅ Deleted address collection answer")
    
    print("\n🎯 NOW TEST THE 'NO' PATH:")
    print("1. Call API → Should show Q_AD_Address_Check (verification)")
    print("2. Answer 'No' → Should show Q_AD_Residential_Address_(Customer-Current) (collection)")
    print("3. This tests the complete 'No' flow path!")

if __name__ == "__main__":
    reset_for_no_test() 