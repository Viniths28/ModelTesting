#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def check_actual_edges():
    with neo_client._driver.session() as session:
        # Check what edges are actually being returned for Q_AD_Number_of_Applicants
        result = session.run("""
            MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})-[e]->(target)
            WHERE type(e) IN ['PRECEDES','TRIGGERS']
            RETURN type(e) as edge_type, e.askWhen as condition, 
                   target.questionId as target_question,
                   target.actionId as target_action,
                   e.orderInForm as order_num
            ORDER BY coalesce(e.orderInForm, e.order, 999)
        """)
        
        records = list(result)
        print(f"Found {len(records)} PRECEDES/TRIGGERS edges from Q_AD_Number_of_Applicants:")
        
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

if __name__ == "__main__":
    check_actual_edges() 