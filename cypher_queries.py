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

def run_query(tx, query, description):
    print(f"\n🔍 {description}")
    print("Query:", query)
    result = tx.run(query)
    records = list(result)
    print("\nResults:")
    for record in records:
        print(record)
    return records

def test_queries(session):
    # 1. List all sections
    query1 = "MATCH (s:Section) RETURN s.sectionId AS Section"
    run_query(session, query1, "All Sections in the database")

    # 2. List all questions with their properties
    query2 = """
    MATCH (q:Question)
    RETURN q.questionId AS QuestionID, 
           q.prompt AS Prompt,
           q.fieldId AS FieldID,
           q.dataType AS DataType
    LIMIT 5
    """
    run_query(session, query2, "Sample Questions with their properties")

    # 3. Questions in order for a specific section
    query3 = """
    MATCH (s:Section {sectionId: 'Get a Quote'})-[r:PRECEDES]->(q:Question)
    RETURN s.sectionId AS Section,
           q.questionId AS Question,
           r.order AS Order
    ORDER BY r.order
    """
    run_query(session, query3, "Questions in 'Get a Quote' section ordered by sequence")

    # 4. Find isolated questions (questions not connected to any section)
    query4 = """
    MATCH (q:Question)
    WHERE NOT EXISTS ((Section)-[:PRECEDES]->(q))
    RETURN q.questionId AS IsolatedQuestion
    """
    run_query(session, query4, "Isolated Questions (if any)")

    # 5. Check relationship properties
    query5 = """
    MATCH (s:Section)-[r:PRECEDES]->(q:Question)
    RETURN s.sectionId AS Section,
           q.questionId AS Question,
           r.order AS Order,
           r.askWhen AS AskWhen
    LIMIT 5
    """
    run_query(session, query5, "Relationship properties sample")

    # 6. Questions grouped by data type
    query6 = """
    MATCH (q:Question)
    RETURN q.dataType AS DataType,
           count(*) AS Count
    """
    run_query(session, query6, "Questions grouped by data type")

    # 7. Find sections with question counts
    query7 = """
    MATCH (s:Section)-[:PRECEDES]->(q:Question)
    RETURN s.sectionId AS Section,
           count(q) AS QuestionCount
    """
    run_query(session, query7, "Sections with their question counts")

try:
    with driver.session() as session:
        test_queries(session)
    print("\n✅ All queries executed successfully!")
except Exception as e:
    print(f"\n❌ Error during query execution: {str(e)}")
finally:
    driver.close() 