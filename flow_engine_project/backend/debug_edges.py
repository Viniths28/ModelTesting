from flow_engine.neo import neo_client
from neo4j import GraphDatabase, basic_auth

# Initialize neo_client with correct credentials  
neo_client._driver = GraphDatabase.driver(
    "bolt://localhost:7689", 
    auth=basic_auth("neo4j", "testpassword")
)

def debug_graph_structure():
    print("🔍 Debugging graph structure...")
    
    with neo_client._driver.session() as s:
        # Check sections
        print("\n📁 SECTIONS:")
        sections = s.run("MATCH (s:Section) RETURN s.sectionId, s.name ORDER BY s.sectionId").data()
        for sec in sections:
            print(f"  {sec['s.sectionId']}: {sec['s.name']}")
        
        # Check questions  
        print("\n❓ QUESTIONS:")
        questions = s.run("MATCH (q:Question) RETURN q.questionId, q.prompt ORDER BY q.questionId").data()
        for q in questions:
            print(f"  {q['q.questionId']}: {q['q.prompt']}")
            
        # Check PRECEDES edges from SEC_COMPLEX
        print("\n➡️  PRECEDES EDGES FROM SEC_COMPLEX:")
        edges = s.run("""
            MATCH (s:Section {sectionId:'SEC_COMPLEX'})-[r:PRECEDES]->(target)
            RETURN type(r) as rel_type, r.orderInForm as order, target.questionId as target_id, target.prompt as target_prompt
            ORDER BY r.orderInForm
        """).data()
        
        if edges:
            for edge in edges:
                print(f"  SEC_COMPLEX -[PRECEDES order:{edge['order']}]-> {edge['target_id']}: {edge['target_prompt']}")
        else:
            print("  ❌ No PRECEDES edges found from SEC_COMPLEX!")
            
        # Check ALL PRECEDES edges
        print("\n🔗 ALL PRECEDES EDGES:")
        all_edges = s.run("""
            MATCH (source)-[r:PRECEDES]->(target)
            RETURN source.sectionId as src_section, source.questionId as src_question, 
                   target.questionId as tgt_question, r.orderInForm as order
            ORDER BY r.orderInForm
        """).data()
        
        for edge in all_edges:
            src = edge['src_section'] or edge['src_question']
            tgt = edge['tgt_question']
            order = edge['order']
            print(f"  {src} -[PRECEDES order:{order}]-> {tgt}")
            
        # Check total relationships
        total_rels = s.run("MATCH ()-[r]->() RETURN count(r) as total").single()
        print(f"\n📊 Total relationships: {total_rels['total']}")

if __name__ == "__main__":
    debug_graph_structure() 