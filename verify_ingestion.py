from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Neo4j credentials from .env
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

# Connect to Neo4j
driver = GraphDatabase.driver(uri, auth=(user, password))

def verify_data(tx):
    # Count sections
    sections_result = tx.run("MATCH (s:Section) RETURN count(s) as section_count")
    section_count = sections_result.single()["section_count"]
    print(f"\n📊 Found {section_count} sections")
    
    # Count questions
    questions_result = tx.run("MATCH (q:Question) RETURN count(q) as question_count")
    question_count = questions_result.single()["question_count"]
    print(f"📝 Found {question_count} questions")
    
    # Count relationships
    relationships_result = tx.run("MATCH ()-[r:PRECEDES]->() RETURN count(r) as rel_count")
    rel_count = relationships_result.single()["rel_count"]
    print(f"🔗 Found {rel_count} PRECEDES relationships")
    
    # Sample of sections with their questions
    print("\n📋 Sample of sections and their questions:")
    sample_result = tx.run("""
        MATCH (s:Section)-[r:PRECEDES]->(q:Question)
        RETURN s.sectionId as section, q.questionId as question, r.order as order
        LIMIT 5
    """)
    
    for record in sample_result:
        print(f"\nSection: {record['section']}")
        print(f"  └─ Question: {record['question']} (Order: {record['order']})")

try:
    with driver.session() as session:
        session.execute_read(verify_data)
    print("\n✅ Verification completed successfully!")
except Exception as e:
    print(f"\n❌ Error during verification: {str(e)}")
finally:
    driver.close() 