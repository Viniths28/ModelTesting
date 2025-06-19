#!/usr/bin/env python
"""Quick utility to (idempotently) create an Application node and an Applicant
node in Neo4j and link them with a HAS_APPLICANT relationship.

Usage
-----
    python create_app_entities.py <applicationId> <applicantId>

If the nodes or the relationship already exist the script does nothing
additional (thanks to the Cypher `MERGE` clauses).

Neo4j connection details are taken from the same environment variables that
`flow_engine` uses, falling back to the defaults documented in the spec.
"""
from __future__ import annotations

import os
import sys
from textwrap import dedent

from neo4j import GraphDatabase, basic_auth
from loguru import logger

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "testpassword")

if len(sys.argv) != 3:
    print(f"Usage: python {sys.argv[0]} <applicationId> <applicantId>")
    sys.exit(1)

application_id = sys.argv[1]
applicant_id = sys.argv[2]

logger.info(
    "Connecting to Neo4j at {} as {}", NEO4J_URI, NEO4J_USER
)

driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))

CYPHER = dedent(
    """
    MERGE (app:Application {applicationId:$applicationId})
    MERGE (person:Applicant {applicantId:$applicantId})
    MERGE (app)-[:HAS_APPLICANT]->(person)
    RETURN id(app)   AS applicationNodeId,
           id(person) AS applicantNodeId
    """
)

with driver.session() as session:
    record = session.run(
        CYPHER, applicationId=application_id, applicantId=applicant_id
    ).single()

    logger.success(
        "Application node id: {} | Applicant node id: {}",
        record["applicationNodeId"],
        record["applicantNodeId"],
    )

driver.close() 