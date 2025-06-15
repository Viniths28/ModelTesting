import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

# Load .env file with NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
load_dotenv()

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Load CSV
df = pd.read_csv("ModelsmokeTest.csv")
df.fillna("", inplace=True)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Step 1: Create Section and Question Nodes
def create_section_question_nodes(tx, row):
    tx.run("""
        MERGE (sec:Section {sectionId: $sectionId})
        ON CREATE SET sec.name = $sectionId
    """, sectionId=row["Section (Node)"])

    tx.run("""
        MERGE (q:Question {questionId: $questionId})
        SET q.prompt = $prompt,
            q.fieldId = $fieldId,
            q.heading = $heading,
            q.stage = $stage,
            q.dataType = $datatype,
            q.exampleAnswer = $exampleAnswer,
            q.sectionOrder = $sectionOrder,
            q.order = $order
    """, questionId=row["Question ID"], 
         prompt=row["Prompt (The Question)"],
         fieldId=row["Field ID"], 
         heading=row["Heading"],
         stage=row["Stage"], 
         datatype=row["Data Type"],
         exampleAnswer=row["Example Answer"],
         sectionOrder=row["Category Order"],
         order=row["Order"])

# Step 2: Create Correct PRECEDES Chain
def link_questions_by_order(tx, section_id, ordered_rows):
    if not ordered_rows:
        return

    # Link Section → First Question
    first = ordered_rows[0]
    tx.run("""
        MATCH (sec:Section {sectionId: $sectionId})
        MATCH (q:Question {questionId: $questionId})
        MERGE (sec)-[r:PRECEDES]->(q)
        SET r.order = $order,
            r.askWhen = $askWhen
    """, sectionId=section_id, questionId=first["Question ID"],
         order=first["Order"], askWhen=first["Ask When"])

    # Link question → question chain
    for i in range(1, len(ordered_rows)):
        q1 = ordered_rows[i - 1]
        q2 = ordered_rows[i]
        tx.run("""
            MATCH (q1:Question {questionId: $qid1})
            MATCH (q2:Question {questionId: $qid2})
            MERGE (q1)-[r:PRECEDES]->(q2)
            SET r.order = $order,
                r.askWhen = $askWhen
        """, qid1=q1["Question ID"], qid2=q2["Question ID"],
             order=q2["Order"], askWhen=q2["Ask When"])

# Run the whole process
with driver.session() as session:
    # Step 1: Create all nodes
    for _, row in df.iterrows():
        session.write_transaction(create_section_question_nodes, row)

    # Step 2: Group and chain questions by Section
    grouped = df.groupby("Section (Node)")
    for section_id, group in grouped:
        ordered = group.sort_values("Category Order").to_dict("records")
        session.write_transaction(link_questions_by_order, section_id, ordered)

driver.close()
print("✅ Sections and Question chains created successfully.")