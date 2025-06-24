#!/usr/bin/env python3

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def analyze_complete_flow():
    print("🔍 COMPLETE ADDRESS SECTION FLOW ANALYSIS")
    print("=" * 60)
    
    section_id = "SEC_1a879403-51e3-4eef-b6c5-00a613f8f76e"
    
    # Get ALL edges from this section
    with neo_client._driver.session() as session:
        result = session.run("""
            MATCH (s:Section {sectionId: $sectionId})-[e:PRECEDES]->(target)
            RETURN e, target.questionId as target_question, 
                   target.questionText as question_text,
                   e.askWhen as condition, 
                   coalesce(e.orderInForm, e.order, 999) as order
            ORDER BY order, id(e)
        """, sectionId=section_id)
        
        edges = list(result)
        print(f"Found {len(edges)} total edges from section:")
        
        for i, edge_record in enumerate(edges):
            target = edge_record['target_question']
            text = edge_record['question_text'] or "No text available"
            condition = edge_record['condition']
            order = edge_record['order']
            
            print(f"\n{i+1}. → {target}")
            print(f"   Text: {text}")
            print(f"   askWhen: {condition}")
            print(f"   order: {order}")

        # Also check edges FROM the address verification question
        print(f"\n{'='*60}")
        print("EDGES FROM Q_AD_Address_Check (verification question)")
        print(f"{'='*60}")
        
        verification_edges = session.run("""
            MATCH (q:Question {questionId: "Q_AD_Address_Check"})-[e:PRECEDES]->(target)
            RETURN e, target.questionId as target_question, 
                   target.questionText as question_text,
                   e.askWhen as condition,
                   coalesce(e.orderInForm, e.order, 999) as order
            ORDER BY order, id(e)
        """)
        
        v_edges = list(verification_edges)
        if v_edges:
            print(f"Found {len(v_edges)} edges from Q_AD_Address_Check:")
            
            for i, edge_record in enumerate(v_edges):
                target = edge_record['target_question']
                text = edge_record['question_text'] or "No text available"
                condition = edge_record['condition']
                order = edge_record['order']
                
                print(f"\n{i+1}. Q_AD_Address_Check → {target}")
                print(f"   Text: {text}")
                print(f"   askWhen: {condition}")
                print(f"   order: {order}")
        else:
            print("No edges found from Q_AD_Address_Check")
        
        # Check current data state
        print(f"\n{'='*60}")
        print("CURRENT DATA STATE")
        print(f"{'='*60}")
        
        data_check = session.run("""
            MATCH (app:Application {applicationId: 'Appl_123'})-[:HAS_APPLICANT]->(a:Applicant {applicantId: 'App001'})
            
            // Check address data
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d1:Datapoint)-[:ANSWERS]->(q1:Question {questionId: "Q_AD_Residential_Address_(Customer-Current)"})
            
            // Check verification answer
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d2:Datapoint)-[:ANSWERS]->(q2:Question {questionId: "Q_AD_Address_Check"})
            
            RETURN d1.value as address_value, d2.value as verification_answer,
                   d1 IS NOT NULL as has_address, d2 IS NOT NULL as has_verification
        """)
        
        data_record = data_check.single()
        if data_record:
            print(f"Address data: {data_record['address_value']} (exists: {data_record['has_address']})")
            print(f"Verification answer: {data_record['verification_answer']} (exists: {data_record['has_verification']})")
        
        # Show what the variables should evaluate to
        print(f"\n{'='*60}")
        print("EXPECTED VARIABLE VALUES")
        print(f"{'='*60}")
        
        if data_record:
            dealer_exists = data_record['has_address']
            verification_answer = data_record['verification_answer'] or ''
            
            print(f"dealer_address_exists: {dealer_exists}")
            print(f"address_verification_answer: '{verification_answer}'")
            
            print(f"\nCondition evaluations:")
            print(f"  dealer_address_exists == True: {dealer_exists == True}")
            print(f"  dealer_address_exists == False: {dealer_exists == False}")
            print(f"  address_verification_answer == 'Yes': {verification_answer == 'Yes'}")
            print(f"  address_verification_answer == 'No': {verification_answer == 'No'}")

if __name__ == "__main__":
    analyze_complete_flow() 