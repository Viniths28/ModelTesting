from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Neo4j credentials
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

# Connect to Neo4j
driver = GraphDatabase.driver(uri, auth=(user, password))

def verify_chains(tx):
    # Get all sections and their questions in order
    result = tx.run("""
        MATCH (s:Section)-[r:PRECEDES]->(q:Question)
        WITH s, q, r
        ORDER BY s.sectionId, r.order
        RETURN s.sectionId as section, 
               COLLECT({id: q.questionId, order: r.order}) as questions
    """)
    
    sections = result.values()
    
    print("\n🔍 Verifying Question Chains:")
    for section in sections:
        section_id = section[0]
        questions = section[1]
        
        print(f"\n📑 Section: {section_id}")
        print("Question Chain:")
        for q in questions:
            print(f"  └─ {q['id']} (Order: {q['order']})")
            
    # Verify question-to-question PRECEDES relationships
    chain_result = tx.run("""
        MATCH (q1:Question)-[r:PRECEDES]->(q2:Question)
        RETURN q1.questionId as from, q2.questionId as to, r.order as order
        ORDER BY r.order
    """)
    
    print("\n🔗 Question-to-Question Relationships:")
    for record in chain_result:
        print(f"  {record['from']} → {record['to']} (Order: {record['order']})")

try:
    with driver.session() as session:
        session.execute_read(verify_chains)
    print("\n✅ Chain verification completed!")
except Exception as e:
    print(f"\n❌ Error during verification: {str(e)}")
finally:
    driver.close() 