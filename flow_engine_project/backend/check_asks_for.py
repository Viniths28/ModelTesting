#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def check_asks_for():
    with neo_client._driver.session() as session:
        result = session.run("""
            MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})-[e:ASKS_FOR]->(target)
            RETURN target, e, labels(target) as target_labels
        """)
        
        records = list(result)
        print(f"Found {len(records)} ASKS_FOR edges")
        
        for record in records:
            target = record['target']
            edge = record['e']
            target_labels = record['target_labels']
            
            print(f"Target: {dict(target)}")
            print(f"Target Labels: {target_labels}")
            print(f"Edge: {dict(edge)}")

if __name__ == "__main__":
    check_asks_for() 