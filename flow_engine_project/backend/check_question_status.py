#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def check_question_status():
    print("📋 CHECKING QUESTION STATUS")
    print("=" * 50)
    
    with neo_client._driver.session() as session:
        result = session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            
            // Check all relevant questions
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d1:Datapoint)-[:ANSWERS]->(q1:Question {questionId: "Q_AD_Residential_Address_(Customer-Current)"})
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d2:Datapoint)-[:ANSWERS]->(q2:Question {questionId: "Q_AD_Address_Check"})
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d3:Datapoint)-[:ANSWERS]->(q3:Question {questionId: "Q_AD_Residential_Status_(Customer)"})
            
            RETURN 
                q1.questionId as addr_q, d1.value as addr_value, d1 IS NOT NULL as addr_answered,
                q2.questionId as check_q, d2.value as check_value, d2 IS NOT NULL as check_answered,
                q3.questionId as status_q, d3.value as status_value, d3 IS NOT NULL as status_answered
        """)
        
        record = result.single()
        if record:
            print("Question Status:")
            print(f"  Q_AD_Residential_Address_(Customer-Current):")
            print(f"    Answered: {record['addr_answered']}")
            print(f"    Value: {record['addr_value']}")
            
            print(f"  Q_AD_Address_Check:")
            print(f"    Answered: {record['check_answered']}")
            print(f"    Value: {record['check_value']}")
            
            print(f"  Q_AD_Residential_Status_(Customer):")
            print(f"    Answered: {record['status_answered']}")
            print(f"    Value: {record['status_value']}")
            
            # Analyze the logic
            print(f"\n{'='*30}")
            print("FLOW LOGIC ANALYSIS")
            print(f"{'='*30}")
            
            if record['check_answered'] and record['check_value'] == 'No':
                print("✅ User answered 'No' to address verification")
                print("📍 According to flow logic:")
                print("   address_verification_answer == 'No' → Should show Q_AD_Residential_Address_(Customer-Current)")
                
                if record['addr_answered']:
                    print(f"❗ BUT Q_AD_Residential_Address_(Customer-Current) is already answered!")
                    print(f"   Value: {record['addr_value']}")
                    print("🔄 Engine continues to next unanswered question")
                else:
                    print("❌ Q_AD_Residential_Address_(Customer-Current) is NOT answered - this is the bug!")
                    
        else:
            print("❌ No data found")

if __name__ == "__main__":
    check_question_status() 