#!/usr/bin/env python3
"""
Debug script to analyze the current flow state and understand why the engine
is returning Q_AD_First_Name instead of proceeding with co-applicant logic.
"""

import sys
import os
import json

# Add the current directory to the path so we can import flow_engine
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def check_datapoints():
    """Check what datapoints exist for the Q_AD_Number_of_Applicants question."""
    print("=== CHECKING DATAPOINTS ===")
    
    with neo_client._driver.session() as session:
        # Check if we have any datapoints for the Number_of_Applicants question
        result = session.run("""
            MATCH (a:Applicant {applicantId: 'App001'})
            OPTIONAL MATCH (a)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: 'Q_AD_Number_of_Applicants'})
            RETURN a, d, q, d.value as answer_value
        """)
        
        records = list(result)
        print(f"Found {len(records)} records for App001 and Q_AD_Number_of_Applicants")
        
        for record in records:
            applicant = record['a']
            datapoint = record['d']
            question = record['q']
            answer_value = record['answer_value']
            
            print(f"Applicant: {dict(applicant)}")
            print(f"Datapoint: {dict(datapoint) if datapoint else 'None'}")
            print(f"Question: {dict(question) if question else 'None'}")
            print(f"Answer Value: {answer_value}")

def check_section_structure():
    """Check the section structure and edges."""
    print("\n=== CHECKING SECTION STRUCTURE ===")
    
    with neo_client._driver.session() as session:
        # Get the section and its variables
        result = session.run("""
            MATCH (s:Section {sectionId: 'SEC_0f962e4d-a932-4958-9352-b54e0ef92be5'})
            RETURN s.name as section_name, s.variables as variables
        """)
        
        record = result.single()
        if record:
            print(f"Section Name: {record['section_name']}")
            print(f"Variables: {record['variables']}")
            
            if record['variables']:
                try:
                    variables = json.loads(record['variables'])
                    print("\nParsed Variables:")
                    for var in variables:
                        print(f"  - {var['name']}: {var.get('cypher', var.get('python', 'No evaluator'))}")
                except json.JSONDecodeError:
                    print("Failed to parse variables JSON")

def check_question_edges():
    """Check the edges from Q_AD_Number_of_Applicants."""
    print("\n=== CHECKING QUESTION EDGES ===")
    
    with neo_client._driver.session() as session:
        # Find edges from the Number_of_Applicants question
        result = session.run("""
            MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})
            MATCH (q)-[e]->(target)
            RETURN q, type(e) as edge_type, e, target, 
                   target.questionId as target_question,
                   target.actionId as target_action,
                   e.askWhen as condition,
                   e.orderInForm as order_num
            ORDER BY coalesce(e.orderInForm, e.order, 999)
        """)
        
        records = list(result)
        print(f"Found {len(records)} edges from Q_AD_Number_of_Applicants")
        
        for i, record in enumerate(records, 1):
            edge_type = record['edge_type']
            condition = record['condition']
            target_question = record['target_question']
            target_action = record['target_action']
            order_num = record['order_num']
            
            target_id = target_question or target_action or 'unknown'
            
            print(f"\nEdge {i}: {edge_type} -> {target_id}")
            print(f"  Order: {order_num}")
            print(f"  Condition: {condition}")

def check_first_question_path():
    """Check why we're getting Q_AD_First_Name."""
    print("\n=== CHECKING FIRST QUESTION PATH ===")
    
    with neo_client._driver.session() as session:
        # Find what leads to Q_AD_First_Name
        result = session.run("""
            MATCH (q:Question {questionId: 'Q_AD_First_Name'})
            OPTIONAL MATCH (source)-[e]->(q)
            RETURN source, type(e) as edge_type, e.askWhen as condition, e.orderInForm as order_num
        """)
        
        records = list(result)
        print(f"Found {len(records)} edges leading to Q_AD_First_Name")
        
        for record in records:
            source = record['source']
            edge_type = record['edge_type']
            condition = record['condition']
            order_num = record['order_num']
            
            source_id = source.get('sectionId') or source.get('questionId') or source.get('actionId') or 'unknown'
            
            print(f"Source: {source_id} -{edge_type}-> Q_AD_First_Name")
            print(f"  Order: {order_num}")
            print(f"  Condition: {condition}")

def test_variable_evaluation():
    """Test the variable evaluation with current context."""
    print("\n=== TESTING VARIABLE EVALUATION ===")
    
    from flow_engine.evaluators import cypher_eval
    
    # Test context
    ctx = {
        'applicationId': 'Appl_123',
        'applicantId': 'App001',
        'sectionId': 'SEC_0f962e4d-a932-4958-9352-b54e0ef92be5',
        'isPrimaryFlow': True
    }
    
    # Test each variable
    variables_to_test = [
        {
            "name": "current_applicant",
            "cypher": "MATCH (a:Applicant {applicantId:$applicantId}) RETURN elementId(a) As value"
        },
        {
            "name": "has_coapplicant",
            "cypher": "MATCH (a:Applicant {applicantId:$applicantId})-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(:Question {questionId:\"Q_AD_Number_of_Applicants\"}) RETURN COALESCE(d.value,'No') AS value"
        },
        {
            "name": "coapplicant_exists",
            "cypher": "MATCH (app:Application {applicationId:$applicationId}) RETURN EXISTS{(app)-[:HAS_APPLICANT]->(:Applicant {type:\"CO_APPLICANT\"})} AS value"
        }
    ]
    
    for var in variables_to_test:
        try:
            result = cypher_eval(var['cypher'], ctx)
            print(f"✓ {var['name']}: {result}")
        except Exception as e:
            print(f"✗ {var['name']}: ERROR - {e}")

def main():
    """Main debug function."""
    print("🔍 FLOW STATE DEBUG ANALYSIS")
    print("=" * 50)
    
    try:
        check_datapoints()
        check_section_structure()
        check_question_edges()
        check_first_question_path()
        test_variable_evaluation()
        
        print("\n" + "=" * 50)
        print("Debug analysis complete!")
        
    except Exception as e:
        print(f"❌ Error during debug analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 