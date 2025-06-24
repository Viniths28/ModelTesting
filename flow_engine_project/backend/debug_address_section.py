#!/usr/bin/env python3

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client
from flow_engine.traversal import walk_section, Context, _load_section_vars

def debug_address_section():
    print("🔍 DEBUGGING ADDRESS SECTION CONFIGURATION")
    print("=" * 60)
    
    section_id = "SEC_1a879403-51e3-4eef-b6c5-00a613f8f76e"
    ctx_dict = {
        'applicationId': 'Appl_123',
        'applicantId': 'App001',
        'sectionId': section_id,
        'isPrimaryFlow': True
    }
    
    print(f"Checking section: {section_id}")
    
    # Step 1: Check if section exists
    with neo_client._driver.session() as session:
        section_check = session.run("""
            MATCH (s:Section {sectionId: $sectionId})
            RETURN s.variables as variables, s.sourceNode as sourceNode, s
        """, sectionId=section_id)
        
        section_record = section_check.single()
        if not section_record:
            print("❌ Section not found in database!")
            return
        
        print("✅ Section found in database")
        section_data = dict(section_record['s'])
        
        print(f"Section sourceNode: {section_record['sourceNode']}")
        print(f"Section variables config: {section_record['variables']}")
        
        # Parse variables if they exist
        if section_record['variables']:
            try:
                variables = json.loads(section_record['variables'])
                print(f"\nParsed variables ({len(variables)} found):")
                for i, var in enumerate(variables):
                    print(f"  {i+1}. {var.get('name', 'UNNAMED')}: {var.get('cypher', var.get('python', 'NO_EVALUATOR'))}")
            except Exception as e:
                print(f"❌ Failed to parse variables: {e}")
        else:
            print("❌ No variables configured in section!")
    
    # Step 2: Check section edges/flow structure
    print(f"\n{'='*30}")
    print("CHECKING SECTION FLOW STRUCTURE")
    print(f"{'='*30}")
    
    with neo_client._driver.session() as session:
        edges_check = session.run("""
            MATCH (s:Section {sectionId: $sectionId})-[e:PRECEDES]->(target)
            RETURN e, target.questionId as target_question, e.askWhen as condition
            ORDER BY coalesce(e.orderInForm, e.order), id(e)
        """, sectionId=section_id)
        
        edges = list(edges_check)
        print(f"Found {len(edges)} edges from section:")
        
        for i, edge_record in enumerate(edges):
            edge = edge_record['e']
            target = edge_record['target_question']
            condition = edge_record['condition']
            print(f"  {i+1}. → {target}")
            print(f"     askWhen: {condition}")
            print(f"     edge properties: {dict(edge)}")
    
    # Step 3: Test variable loading
    print(f"\n{'='*30}")
    print("TESTING VARIABLE LOADING")
    print(f"{'='*30}")
    
    try:
        var_defs = _load_section_vars(section_id)
        print(f"Loaded variables: {list(var_defs.keys())}")
        
        if not var_defs:
            print("❌ No variables loaded - check section configuration")
            return
        
        # Test each variable
        ctx = Context(
            input_params=ctx_dict,
            var_defs=var_defs
        )
        
        for var_name in var_defs.keys():
            try:
                print(f"\nTesting variable '{var_name}':")
                print(f"  Evaluator: {var_defs[var_name]}")
                
                resolved_value = ctx.resolve_var(var_name)
                print(f"  Result: {resolved_value} (type: {type(resolved_value)})")
                
                if isinstance(resolved_value, list) and len(resolved_value) == 0:
                    print(f"  ⚠️  WARNING: Variable '{var_name}' returned empty array!")
                
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
        
    except Exception as e:
        print(f"❌ Failed to load variables: {e}")
    
    # Step 4: Test actual engine call
    print(f"\n{'='*30}")
    print("TESTING ENGINE CALL")
    print(f"{'='*30}")
    
    try:
        result = walk_section(section_id, ctx_dict)
        print("✅ Engine call succeeded")
        print(f"Result: {json.dumps(result, indent=2, default=str)}")
    except Exception as e:
        print("❌ Engine call failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_address_section() 