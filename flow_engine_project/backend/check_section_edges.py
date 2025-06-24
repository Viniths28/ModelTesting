#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def check_section_edges():
    with neo_client._driver.session() as session:
        # Check what edges exist from the section
        result = session.run("""
            MATCH (s:Section {sectionId: 'SEC_0f962e4d-a932-4958-9352-b54e0ef92be5'})-[e]->(target)
            WHERE type(e) IN ['PRECEDES','TRIGGERS']
            RETURN type(e) as edge_type, e.askWhen as condition, 
                   target.questionId as target_question,
                   target.actionId as target_action,
                   e.orderInForm as order_num
            ORDER BY coalesce(e.orderInForm, e.order, 999)
        """)
        
        records = list(result)
        print(f"Found {len(records)} PRECEDES/TRIGGERS edges from Section:")
        
        for i, record in enumerate(records, 1):
            edge_type = record['edge_type']
            condition = record['condition']
            target_question = record['target_question']
            target_action = record['target_action']
            order_num = record['order_num']
            
            target_id = target_question or target_action or 'unknown'
            condition_str = condition if condition else "No condition (always true)"
            
            print(f"  {i}. {edge_type} -> {target_id}")
            print(f"     Condition: {condition_str}")
            print(f"     Order: {order_num}")
            print()

        # Also check what leads to Q_AD_First_Name specifically
        print("=" * 50)
        print("CHECKING WHAT LEADS TO Q_AD_First_Name:")
        
        result2 = session.run("""
            MATCH (source)-[e:PRECEDES]->(q:Question {questionId: 'Q_AD_First_Name'})
            RETURN source, e.askWhen as condition, e.orderInForm as order_num,
                   source.sectionId as source_section,
                   source.questionId as source_question,
                   source.actionId as source_action
            ORDER BY coalesce(e.orderInForm, e.order, 999)
        """)
        
        records2 = list(result2)
        print(f"Found {len(records2)} PRECEDES edges leading to Q_AD_First_Name:")
        
        for i, record in enumerate(records2, 1):
            condition = record['condition']
            order_num = record['order_num']
            source_section = record['source_section']
            source_question = record['source_question']
            source_action = record['source_action']
            
            source_id = source_section or source_question or source_action or 'unknown'
            condition_str = condition if condition else "No condition (always true)"
            
            print(f"  {i}. {source_id} -PRECEDES-> Q_AD_First_Name")
            print(f"     Condition: {condition_str}")
            print(f"     Order: {order_num}")
            print()

if __name__ == "__main__":
    check_section_edges() 