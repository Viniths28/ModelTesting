#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flow_engine.neo import neo_client

def run_cypher(query: str, params: dict = None):
    """Execute a Cypher query and return results."""
    if params is None:
        params = {}
    with neo_client._driver.session() as session:
        result = session.run(query, **params)
        return [record.data() for record in result]

def check_created_nodes():
    """Check what nodes were actually created."""
    
    applicant_id = "App001"
    created_node_id = "4:163667f3-0018-494d-a3f3-415ecb90e442:164"  # From the response
    
    print("🔍 CHECKING CREATED NODES")
    print("=" * 50)
    
    # Check what the created node actually is
    created_node_check = run_cypher(
        "MATCH (n) WHERE elementId(n) = $node_id RETURN n, labels(n) as labels",
        {"node_id": created_node_id}
    )
    print(f"1. Created node {created_node_id}:")
    for result in created_node_check:
        print(f"   - Labels: {result['labels']}")
        print(f"   - Properties: {dict(result['n'])}")
    
    # Check all nodes connected to the applicant
    applicant_connections = run_cypher(
        """
        MATCH (a:Applicant {applicantId: $app_id})-[r]->(connected)
        RETURN type(r) as relationship, labels(connected) as target_labels, connected
        """,
        {"app_id": applicant_id}
    )
    print(f"\n2. All nodes connected to applicant {applicant_id}:")
    for conn in applicant_connections:
        print(f"   - {conn['relationship']} → {conn['target_labels']}")
    
    # Specifically look for AddressHistory nodes
    all_address_history = run_cypher(
        "MATCH (h:AddressHistory) RETURN elementId(h) as id, h"
    )
    print(f"\n3. All AddressHistory nodes in database:")
    for hist in all_address_history:
        print(f"   - ID: {hist['id']}")
        print(f"   - Properties: {dict(hist['h'])}")
    
    # Check if there's a HAS_HISTORY relationship
    has_history = run_cypher(
        """
        MATCH (a:Applicant {applicantId: $app_id})-[:HAS_HISTORY]->(h)
        RETURN elementId(h) as id, labels(h) as labels, h
        """,
        {"app_id": applicant_id}
    )
    print(f"\n4. Nodes connected via HAS_HISTORY:")
    for hist in has_history:
        print(f"   - ID: {hist['id']}, Labels: {hist['labels']}")

if __name__ == "__main__":
    check_created_nodes() 