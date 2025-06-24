#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client
from flow_engine.traversal import _question_answered, _get_source_node_id

def test_question_answered():
    print("🔍 TESTING _question_answered FUNCTION")
    print("=" * 50)
    
    # Test context - this should be the source node (applicant)
    with neo_client._driver.session() as session:
        # Get the source node (applicant)
        result = session.run("""
            MATCH (a:Applicant {applicantId: 'App001'})
            RETURN a, elementId(a) as element_id
        """)
        
        record = result.single()
        if not record:
            print("❌ No applicant found with applicantId: App001")
            return
            
        source_node = record['a']
        element_id = record['element_id']
        
        print(f"Source Node (Applicant): {dict(source_node)}")
        print(f"Element ID: {element_id}")
        
        # Test _get_source_node_id function
        source_node_id = _get_source_node_id(source_node)
        print(f"_get_source_node_id result: {source_node_id} (type: {type(source_node_id)})")
        
        print("\n" + "=" * 30)
        print("TESTING QUESTIONS:")
        
        # Test questions we know about
        questions_to_test = [
            "Q_AD_First_Name",
            "Q_AD_Number_of_Applicants",
            "Q_AD_Last_Name"
        ]
        
        for question_id in questions_to_test:
            print(f"\n🔍 Testing: {question_id}")
            
            # First, check manually if datapoint exists
            manual_check = session.run("""
                MATCH (a:Applicant {applicantId: 'App001'})
                OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: $qid})
                RETURN d, q, d.value as answer_value
            """, qid=question_id)
            
            manual_record = manual_check.single()
            if manual_record and manual_record['d']:
                print(f"  ✅ Manual check: Datapoint exists")
                print(f"     Answer value: {manual_record['answer_value']}")
            else:
                print(f"  ❌ Manual check: No datapoint found")
            
            # Now test the _question_answered function
            try:
                is_answered = _question_answered(source_node, question_id)
                print(f"  _question_answered result: {is_answered}")
                
                if manual_record and manual_record['d'] and not is_answered:
                    print(f"  🚨 MISMATCH: Manual check found datapoint but _question_answered returned False!")
                elif not (manual_record and manual_record['d']) and is_answered:
                    print(f"  🚨 MISMATCH: Manual check found no datapoint but _question_answered returned True!")
                else:
                    print(f"  ✅ Results match")
                    
            except Exception as e:
                print(f"  ❌ _question_answered failed: {e}")
        
        print("\n" + "=" * 30)
        print("DEBUGGING _question_answered LOGIC:")
        
        # Let's manually run the exact query from _question_answered
        question_id = "Q_AD_First_Name"
        print(f"\nTesting _question_answered logic for: {question_id}")
        
        # Check what type of ID we're working with
        if isinstance(source_node_id, int):
            where_clause = "id(src) = $srcId"
            print(f"Using integer ID: {source_node_id}")
        else:
            where_clause = "elementId(src) = $srcId"
            print(f"Using element ID: {source_node_id}")
        
        cypher = f"""
        MATCH (src)
        WHERE {where_clause}
        MATCH (src)-[:SUPPLIES]->(:Datapoint)-[:ANSWERS]->(q {{questionId:$qid}})
        RETURN q LIMIT 1
        """
        
        print(f"Query: {cypher}")
        print(f"Parameters: srcId={source_node_id}, qid={question_id}")
        
        debug_result = session.run(cypher, srcId=source_node_id, qid=question_id)
        debug_record = debug_result.single()
        
        if debug_record:
            print(f"✅ Query returned: {dict(debug_record['q'])}")
        else:
            print(f"❌ Query returned no results")
            
            # Let's see what's in the database
            print("\nDebugging - checking what's actually in the database:")
            
            debug_query = """
            MATCH (a:Applicant {applicantId: 'App001'})-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question)
            RETURN q.questionId as question_id, d.value as answer_value
            ORDER BY q.questionId
            """
            
            debug_results = session.run(debug_query)
            debug_records = list(debug_results)
            
            print(f"Found {len(debug_records)} answered questions:")
            for record in debug_records:
                print(f"  - {record['question_id']}: {record['answer_value']}")

if __name__ == "__main__":
    test_question_answered() 