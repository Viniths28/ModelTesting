import sys
sys.path.append('.')
from flow_engine.neo import neo_client

def check_complex_graph():
    driver = neo_client._driver
    
    # First check what node types exist
    with driver.session() as session:
        result = session.run('MATCH (n) RETURN DISTINCT labels(n) as labels, count(n) as count ORDER BY labels')
        node_types = []
        for r in result:
            node_types.append((r['labels'], r['count']))
    print(f'Node types in DB: {node_types}')
    
    # Check all sections with their properties
    with driver.session() as session:
        result = session.run('MATCH (s:Section) RETURN s')
        section_details = []
        for r in result:
            section_details.append(dict(r['s']))
    print(f'Section details: {section_details}')
    
    # Check all questions with their properties
    with driver.session() as session:
        result = session.run('MATCH (q:Question) RETURN q')
        question_details = []
        for r in result:
            question_details.append(dict(r['q']))
    print(f'Question details: {question_details}')
    
    # Extract section and question IDs
    sections = [s.get('sectionId') for s in section_details if s.get('sectionId')]
    questions = [q.get('questionId') for q in question_details if q.get('questionId')]
    
    print(f'All sections in DB: {sections}')
    print(f'All questions in DB: {questions}')
    
    # Check if SEC_COMPLEX exists
    sec_complex_exists = 'SEC_COMPLEX' in sections
    print(f'SEC_COMPLEX exists: {sec_complex_exists}')
    
    # Check actions
    with driver.session() as session:
        result = session.run('MATCH (a:Action) RETURN a.actionId ORDER BY a.actionId')
        actions = [r['actionId'] for r in result if 'actionId' in r]
    print(f'All actions in DB: {actions}')
    
    # Check total nodes
    with driver.session() as session:
        result = session.run('MATCH (n) RETURN count(n) as total')
        total = result.single()['total']
    print(f'Total nodes: {total}')
    
    # Check if expected complex graph nodes exist
    expected_sections = ['SEC_COMPLEX', 'SEC_TARGET', 'SEC_FINISH']
    expected_questions = ['Q_COMPLEX_1', 'Q_COMPLEX_2', 'Q_TARGET_1', 'Q_TARGET_2', 'Q_FINISH_1']
    expected_actions = ['ACT_CREATE_PROP', 'ACT_MARK_COMPLETE', 'ACT_MARK_TARGET_COMPLETE']
    
    missing_sections = [s for s in expected_sections if s not in sections]
    missing_questions = [q for q in expected_questions if q not in questions]
    missing_actions = [a for a in expected_actions if a not in actions]
    
    print(f'\nMissing sections: {missing_sections}')
    print(f'Missing questions: {missing_questions}')
    print(f'Missing actions: {missing_actions}')
    
    is_complete = len(missing_sections) == 0 and len(missing_questions) == 0 and len(missing_actions) == 0
    print(f'\nComplex graph is fully loaded: {is_complete}')
    
    return is_complete

if __name__ == '__main__':
    check_complex_graph() 