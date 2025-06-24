#!/usr/bin/env python3

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client
from flow_engine.traversal import walk_section, Context, _load_section_vars

def debug_neo4j_objects():
    print("🔍 DEBUGGING NEO4J OBJECT SERIALIZATION ISSUE")
    print("=" * 60)
    
    # First test - simulate after answering relationship question
    ctx_dict = {
        'applicationId': 'Appl_123',
        'applicantId': 'App001',
        'sectionId': 'SEC_0f962e4d-a932-4958-9352-b54e0ef92be5',
        'isPrimaryFlow': True
    }
    
    print("Testing with parameters:", ctx_dict)
    
    # Check if there are any answers for the relationship question
    with neo_client._driver.session() as session:
        check_answers = session.run("""
            MATCH (a:Applicant {applicantId: $applicantId})-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: 'Q_AD_Relationship_With_SecondApplicant'})
            RETURN d.value as answer
        """, applicantId=ctx_dict['applicantId'])
        
        answer_record = check_answers.single()
        if answer_record:
            print(f"Relationship question answered: {answer_record['answer']}")
        else:
            print("Relationship question not answered yet")
    
    # Load section variables to see if any return Neo4j objects
    print(f"\n{'='*30}")
    print("CHECKING SECTION VARIABLES")
    print(f"{'='*30}")
    
    var_defs = _load_section_vars(ctx_dict['sectionId'])
    ctx = Context(
        input_params=ctx_dict,
        var_defs=var_defs
    )
    
    for var_name in var_defs.keys():
        try:
            resolved_value = ctx.resolve_var(var_name)
            print(f"Variable '{var_name}': {resolved_value} (type: {type(resolved_value)})")
            
            # Check if it's a Neo4j object
            if hasattr(resolved_value, '__class__') and 'neo4j' in str(type(resolved_value)):
                print(f"  ⚠️  WARNING: Variable '{var_name}' contains Neo4j object!")
                
        except Exception as e:
            print(f"Variable '{var_name}': ERROR - {e}")
    
    # Test the actual walk_section call
    print(f"\n{'='*30}")
    print("TESTING walk_section CALL")
    print(f"{'='*30}")
    
    try:
        result = walk_section(ctx_dict['sectionId'], ctx_dict)
        print("✅ walk_section succeeded")
        
        # Check result for Neo4j objects
        def check_for_neo4j_objects(obj, path=""):
            if hasattr(obj, '__class__') and 'neo4j' in str(type(obj)):
                print(f"  ⚠️  Neo4j object found at {path}: {type(obj)}")
                return True
            elif isinstance(obj, dict):
                found = False
                for k, v in obj.items():
                    if check_for_neo4j_objects(v, f"{path}.{k}"):
                        found = True
                return found
            elif isinstance(obj, list):
                found = False
                for i, v in enumerate(obj):
                    if check_for_neo4j_objects(v, f"{path}[{i}]"):
                        found = True
                return found
            return False
        
        print("Checking result for Neo4j objects...")
        if check_for_neo4j_objects(result):
            print("❌ Found Neo4j objects in result - this will cause JSON serialization errors")
        else:
            print("✅ No Neo4j objects found in result")
            
        print(f"\nResult preview: {json.dumps(result, indent=2, default=str)[:500]}...")
        
    except Exception as e:
        print(f"❌ walk_section failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_neo4j_objects() 