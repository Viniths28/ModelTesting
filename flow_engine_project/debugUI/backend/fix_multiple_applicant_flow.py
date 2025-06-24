#!/usr/bin/env python3
"""
Script to fix the multiple applicant creation issue by adding an additional edge
to handle the case where coapplicant exists and relationship has been answered.
"""

import sys
import os
from loguru import logger

# Add the parent backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from flow_engine.neo import neo_client

def add_completion_edge():
    """Add the additional edge to handle completed multiple applicant flow."""
    
    logger.info("Adding completion edge for multiple applicant flow...")
    
    with neo_client._driver.session() as session:
        # First, let's check the current flow structure
        logger.info("Checking current flow structure...")
        
        result = session.run("""
            MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})
            MATCH (q)-[e]->(target)
            RETURN q, e, target, type(e) as edgeType, e.askWhen as condition
            ORDER BY coalesce(e.orderInForm, e.order, 999)
        """)
        
        current_edges = result.values()
        logger.info(f"Found {len(current_edges)} existing edges from Q_AD_Number_of_Applicants")
        
        for i, (q, e, target, edge_type, condition) in enumerate(current_edges, 1):
            target_id = target.get('questionId') or target.get('actionId') or target.get('sectionId', 'unknown')
            logger.info(f"  Edge {i}: {edge_type} -> {target_id}")
            logger.info(f"    Condition: {condition}")
        
        # Check if our completion edge already exists
        completion_check = session.run("""
            MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})
            MATCH (q)-[e]->(a:Action)
            WHERE e.askWhen CONTAINS 'relationship_answered'
            RETURN count(e) as existing_count
        """).single()
        
        if completion_check['existing_count'] > 0:
            logger.warning("Completion edge with 'relationship_answered' condition already exists!")
            return False
        
        # Find the CompleteSection action
        complete_action = session.run("""
            MATCH (a:Action)
            WHERE a.actionType = 'CompleteSection'
            RETURN a LIMIT 1
        """).single()
        
        if not complete_action:
            logger.error("CompleteSection action not found!")
            return False
        
        action_node = complete_action['a']
        logger.info(f"Found CompleteSection action: {action_node.get('actionId', 'unknown')}")
        
        # Add the new completion edge
        logger.info("Adding new completion edge...")
        
        result = session.run("""
            MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})
            MATCH (a:Action {actionType: 'CompleteSection'})
            CREATE (q)-[e:PRECEDES {
                askWhen: "{{ has_coapplicant }} == 'Yes' and {{ coapplicant_exists }} and {{ relationship_answered }}",
                orderInForm: 4,
                description: "Complete section when coapplicant exists and relationship is answered"
            }]->(a)
            RETURN e
        """)
        
        new_edge = result.single()
        if new_edge:
            logger.success("✅ Successfully added completion edge!")
            
            # Verify the new flow structure
            logger.info("Verifying updated flow structure...")
            
            result = session.run("""
                MATCH (q:Question {questionId: 'Q_AD_Number_of_Applicants'})
                MATCH (q)-[e]->(target)
                RETURN q, e, target, type(e) as edgeType, e.askWhen as condition
                ORDER BY coalesce(e.orderInForm, e.order, 999)
            """)
            
            updated_edges = result.values()
            logger.info(f"Updated flow now has {len(updated_edges)} edges:")
            
            for i, (q, e, target, edge_type, condition) in enumerate(updated_edges, 1):
                target_id = target.get('questionId') or target.get('actionId') or target.get('sectionId', 'unknown')
                logger.info(f"  Edge {i}: {edge_type} -> {target_id}")
                logger.info(f"    Condition: {condition}")
            
            return True
        else:
            logger.error("Failed to create completion edge!")
            return False

def verify_variables():
    """Verify that the required variables are properly defined."""
    
    logger.info("Verifying required variables...")
    
    with neo_client._driver.session() as session:
        # Check for section-level variables
        result = session.run("""
            MATCH (s:Section {sectionId: 'SEC_APPLICANT_DETAILS'})
            RETURN s.variables as variables
        """).single()
        
        if result and result['variables']:
            import json
            try:
                variables = json.loads(result['variables'])
                var_names = [var['name'] for var in variables]
                
                required_vars = ['has_coapplicant', 'coapplicant_exists', 'relationship_answered', 'isPrimaryFlow']
                missing_vars = [var for var in required_vars if var not in var_names]
                
                if missing_vars:
                    logger.warning(f"Missing required variables: {missing_vars}")
                    logger.info("You may need to add these variable definitions to your section")
                else:
                    logger.success("✅ All required variables are defined!")
                
                logger.info(f"Found variables: {var_names}")
                
            except json.JSONDecodeError:
                logger.error("Failed to parse section variables JSON")
        else:
            logger.warning("No section-level variables found")

def main():
    """Main function to fix the multiple applicant flow."""
    
    logger.info("🔧 Flow Engine Multiple Applicant Fix")
    logger.info("=" * 50)
    
    try:
        # Test Neo4j connection
        with neo_client._driver.session() as session:
            session.run("RETURN 1").single()
        logger.success("✅ Neo4j connection established")
        
        # Verify variables
        verify_variables()
        
        # Add completion edge
        success = add_completion_edge()
        
        if success:
            logger.success("🎉 Multiple applicant flow fix completed successfully!")
            logger.info("")
            logger.info("The flow now has proper completion logic:")
            logger.info("1. First time (Yes + isPrimaryFlow + no coapplicant) → Create coapplicant")
            logger.info("2. Second time (Yes + coapplicant exists + no relationship) → Ask relationship")
            logger.info("3. Third time (Yes + coapplicant exists + relationship answered) → Complete section")
            logger.info("4. Any time (No) → Complete section")
            logger.info("")
            logger.info("Test the flow using the debug UI to verify the fix!")
        else:
            logger.error("❌ Failed to fix multiple applicant flow")
            return 1
            
    except Exception as e:
        logger.exception("❌ Error during fix: {}", e)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 