#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client
from flow_engine.traversal import _question_answered, _get_source_node_id, Context, _load_section_vars

def trace_engine_flow():
    print("🔍 TRACING ENGINE FLOW STEP BY STEP")
    print("=" * 60)
    
    # Set up the context like the real engine does
    ctx_dict = {
        'applicationId': 'Appl_123',
        'applicantId': 'App001',
        'sectionId': 'SEC_0f962e4d-a932-4958-9352-b54e0ef92be5',
        'isPrimaryFlow': True
    }
    
    section_id = ctx_dict['sectionId']
    
    # Load variables like the engine does
    var_defs = _load_section_vars(section_id)
    print(f"Loaded {len(var_defs)} section variables:")
    for name, var_def in var_defs.items():
        evaluator = var_def.get('cypher', var_def.get('python', 'No evaluator'))
        print(f"  - {name}: {evaluator[:50]}...")
    
    # Create context
    ctx = Context(
        input_params=ctx_dict,
        var_defs=var_defs
    )
    
    print(f"\n{'='*30}")
    print("STEP 1: ENGINE STARTS FROM SECTION")
    print(f"{'='*30}")
    
    with neo_client._driver.session() as session:
        # Get the section node
        section_result = session.run("""
            MATCH (s:Section {sectionId: $sectionId})
            RETURN s, elementId(s) as element_id
        """, sectionId=section_id)
        
        section_record = section_result.single()
        if not section_record:
            print("❌ Section not found")
            return
            
        section_node = section_record['s']
        print(f"Section: {dict(section_node)}")
        
        # Get outgoing edges from section (like _fetch_outgoing_edges does)
        edges_result = session.run("""
            MATCH (s:Section {sectionId: $sectionId})-[e]->(t)
            WHERE type(e) IN ['PRECEDES','TRIGGERS']
            RETURN e, t
            ORDER BY coalesce(e.orderInForm, e.order), id(e)
        """, sectionId=section_id)
        
        edges = list(edges_result)
        print(f"\nFound {len(edges)} outgoing edges from section:")
        
        for i, record in enumerate(edges, 1):
            edge = record['e']
            target = record['t']
            
            edge_type = edge.type
            ask_when = edge.get('askWhen')
            target_question_id = target.get('questionId')
            target_action_id = target.get('actionId')
            
            target_id = target_question_id or target_action_id or 'unknown'
            
            print(f"  {i}. {edge_type} -> {target_id}")
            print(f"     askWhen: {ask_when or 'None (always true)'}")
            
            # This is the first edge the engine will process
            if i == 1:
                print(f"\n{'='*30}")
                print(f"STEP 2: PROCESSING FIRST EDGE")
                print(f"{'='*30}")
                
                if edge_type == 'PRECEDES' and target_question_id:
                    print(f"Target is Question: {target_question_id}")
                    
                    # Check if question is answered (this is the key step)
                    print(f"\nChecking if {target_question_id} is answered...")
                    
                    # We need to determine the source node for this check
                    # The engine uses ctx.source_node, which starts as None
                    print(f"Current ctx.source_node: {ctx.source_node}")
                    
                    # The engine should resolve source node from the edge or use default
                    # Let's see what the section's default source node should be
                    
                    # For applicant sections, the source node is typically the applicant
                    applicant_result = session.run("""
                        MATCH (a:Applicant {applicantId: $applicantId})
                        RETURN a
                    """, applicantId=ctx_dict['applicantId'])
                    
                    applicant_record = applicant_result.single()
                    if applicant_record:
                        applicant_node = applicant_record['a']
                        print(f"Using applicant as source node: {dict(applicant_node)}")
                        
                        # Test if question is answered
                        is_answered = _question_answered(applicant_node, target_question_id)
                        print(f"_question_answered({target_question_id}): {is_answered}")
                        
                        if is_answered:
                            print(f"✅ Question {target_question_id} is answered - should continue traversal")
                            print("🔄 Engine should now traverse INTO this question to follow its outgoing edges")
                            
                            # Let's check what happens when we traverse into the question
                            print(f"\n{'='*30}")
                            print(f"STEP 3: TRAVERSING INTO {target_question_id}")
                            print(f"{'='*30}")
                            
                            # Get outgoing edges from the question
                            question_edges_result = session.run("""
                                MATCH (q:Question {questionId: $questionId})-[e]->(t)
                                WHERE type(e) IN ['PRECEDES','TRIGGERS']
                                RETURN e, t
                                ORDER BY coalesce(e.orderInForm, e.order), id(e)
                            """, questionId=target_question_id)
                            
                            question_edges = list(question_edges_result)
                            print(f"Found {len(question_edges)} outgoing edges from {target_question_id}:")
                            
                            for j, q_record in enumerate(question_edges, 1):
                                q_edge = q_record['e']
                                q_target = q_record['t']
                                
                                q_edge_type = q_edge.type
                                q_ask_when = q_edge.get('askWhen')
                                q_target_question_id = q_target.get('questionId')
                                q_target_action_id = q_target.get('actionId')
                                
                                q_target_id = q_target_question_id or q_target_action_id or 'unknown'
                                
                                print(f"  {j}. {q_edge_type} -> {q_target_id}")
                                print(f"     askWhen: {q_ask_when or 'None (always true)'}")
                                
                                # Evaluate the askWhen condition
                                if q_ask_when:
                                    print(f"     Evaluating condition: {q_ask_when}")
                                    
                                    # Resolve variables needed for evaluation
                                    if 'has_coapplicant' in q_ask_when:
                                        has_coapplicant = ctx.resolve_var('has_coapplicant')
                                        print(f"     has_coapplicant = {has_coapplicant}")
                                    
                                    if 'coapplicant_exists' in q_ask_when:
                                        coapplicant_exists = ctx.resolve_var('coapplicant_exists')
                                        print(f"     coapplicant_exists = {coapplicant_exists}")
                                    
                                    if 'isPrimaryFlow' in q_ask_when:
                                        isPrimaryFlow = ctx.resolve_var('isPrimaryFlow') or ctx_dict.get('isPrimaryFlow')
                                        print(f"     isPrimaryFlow = {isPrimaryFlow}")
                                
                        else:
                            print(f"❌ Question {target_question_id} is NOT answered - engine stops here")
                            print("🛑 This is why we get this question returned")

if __name__ == "__main__":
    trace_engine_flow() 