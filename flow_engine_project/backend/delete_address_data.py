#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def delete_address_data():
    print("🗑️  DELETING ADDRESS TEST DATA")
    print("=" * 50)
    
    with neo_client._driver.session() as session:
        result = session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: "Q_AD_Residential_Address_(Customer-Current)"})
            WITH d, count(d) as found_count
            FOREACH (dp IN CASE WHEN d IS NOT NULL THEN [d] ELSE [] END |
                DETACH DELETE dp
            )
            RETURN found_count
        """)
        
        record = result.single()
        if record:
            count = record['found_count']
            if count > 0:
                print(f"✅ Deleted {count} address datapoint(s)")
            else:
                print("ℹ️  No address data found to delete")
        else:
            print("❌ Failed to delete address data")
    
    print("\n🎯 EXPECTED FLOW BEHAVIOR:")
    print("   dealer_address_exists = False")
    print("   → Should show: Q_AD_Residential_Address_(Customer-Current) (collection question)")

if __name__ == "__main__":
    delete_address_data() 