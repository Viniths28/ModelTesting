#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def analyze_and_fix_asks_for():
    with neo_client._driver.session() as session:
        # First, let's see what this Field is
        print("=== ANALYZING PROBLEMATIC ASKS_FOR EDGE ===")
        
        result = session.run("""
            MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})-[e:ASKS_FOR]->(f:Field)
            RETURN q, e, f, 
                   f.name as field_name,
                   f.label as field_label,
                   f.description as field_description
        """)
        
        records = list(result)
        for record in records:
            field_name = record['field_name']
            field_label = record['field_label']
            field_description = record['field_description']
            
            print(f"ASKS_FOR Field: {field_name}")
            print(f"Field Label: {field_label}")
            print(f"Field Description: {field_description}")
            
            # This edge is problematic because:
            # 1. It has no condition (always executes)
            # 2. It points to a Field, not a Question
            # 3. This causes the engine to default to the first question
            
            print("\n=== RECOMMENDED ACTION ===")
            print("This ASKS_FOR edge should be DELETED because:")
            print("1. It has no condition (always executes first)")
            print("2. It points to a Field instead of a Question")
            print("3. This causes the engine to ignore your conditional logic")
            
            # Ask for confirmation to delete
            response = input("\nDo you want to DELETE this problematic edge? (y/n): ").lower().strip()
            
            if response == 'y' or response == 'yes':
                print("\nDeleting the problematic ASKS_FOR edge...")
                
                delete_result = session.run("""
                    MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})-[e:ASKS_FOR]->(f:Field)
                    DELETE e
                    RETURN count(e) as deleted_count
                """)
                
                delete_record = delete_result.single()
                deleted_count = delete_record['deleted_count']
                
                print(f"✅ Successfully deleted {deleted_count} ASKS_FOR edge(s)")
                
                # Verify the fix
                print("\n=== VERIFYING FIX ===")
                verify_result = session.run("""
                    MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})-[e]->(target)
                    RETURN type(e) as edge_type, e.askWhen as condition, 
                           target.questionId as target_question,
                           target.actionId as target_action
                    ORDER BY coalesce(e.orderInForm, e.order, 999)
                """)
                
                verify_records = list(verify_result)
                print(f"Remaining edges from Q_AD_Number_of_Applicants: {len(verify_records)}")
                
                for i, record in enumerate(verify_records, 1):
                    edge_type = record['edge_type']
                    condition = record['condition']
                    target_question = record['target_question']
                    target_action = record['target_action']
                    
                    target_id = target_question or target_action or 'unknown'
                    condition_str = condition if condition else "No condition (always true)"
                    
                    print(f"  {i}. {edge_type} -> {target_id}")
                    print(f"     Condition: {condition_str}")
                
                print("\n✅ Fix completed! Your conditional logic should now work properly.")
                
            else:
                print("❌ Edge not deleted. The flow issue will persist.")

def main():
    print("🔧 FIXING ASKS_FOR EDGE ISSUE")
    print("=" * 50)
    
    try:
        analyze_and_fix_asks_for()
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 