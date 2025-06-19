// Create main section
CREATE (secMain:Section {
    sectionId: 'SEC_APPLICANT_INFO',
    name: 'Applicant Information',
    inputParams: ['applicationId', 'applicantId']
});

// Create the second applicant question
CREATE (qSecondAppl:Question {
    questionId: 'Q_SECOND_APPLICANT',
    prompt: 'Are you applying with second applicant?',
    fieldId: 'F_SECOND_APPLICANT',
    dataType: 'boolean',
    exampleAnswer: 'yes/no',
    orderInForm: 1
});

// Create questions for Yes path (second applicant)
CREATE (qSecondName:Question {
    questionId: 'Q_SECOND_NAME',
    prompt: 'What is the second applicant name?',
    fieldId: 'F_SECOND_NAME',
    dataType: 'string',
    orderInForm: 2
});

CREATE (qSecondDOB:Question {
    questionId: 'Q_SECOND_DOB',
    prompt: 'What is the second applicant date of birth?',
    fieldId: 'F_SECOND_DOB',
    dataType: 'date',
    orderInForm: 3
});

// Create questions for No path (single applicant)
CREATE (qSingleIncome:Question {
    questionId: 'Q_SINGLE_INCOME',
    prompt: 'What is your annual income?',
    fieldId: 'F_SINGLE_INCOME',
    dataType: 'number',
    orderInForm: 2
});

// Create relationships with proper askWhen conditions

// Initial question connection
CREATE (secMain)-[:PRECEDES {
    orderInForm: 1,
    sourceNode: 'cypher: MATCH (app:Application {applicationId:$applicationId})-[:HAS_APPLICANT]->(a:Applicant {applicantId:$applicantId}) RETURN a'
}]->(qSecondAppl);

// Yes path - Second applicant questions
CREATE (qSecondAppl)-[:PRECEDES {
    orderInForm: 2,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"yes"})-[:ANSWERS]->(q:Question {questionId:"Q_SECOND_APPLICANT"}) RETURN d',
    variables: '[{"name":"second_applicant_answer","cypher":"MATCH (src)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId:\'Q_SECOND_APPLICANT\'}) RETURN d"}]'
}]->(qSecondName);

CREATE (qSecondName)-[:PRECEDES {
    orderInForm: 3,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"yes"})-[:ANSWERS]->(q:Question {questionId:"Q_SECOND_APPLICANT"}) RETURN d'
}]->(qSecondDOB);

// No path - Single applicant questions
CREATE (qSecondAppl)-[:PRECEDES {
    orderInForm: 2,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"no"})-[:ANSWERS]->(q:Question {questionId:"Q_SECOND_APPLICANT"}) RETURN d',
    variables: '[{"name":"second_applicant_answer","cypher":"MATCH (src)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId:\'Q_SECOND_APPLICANT\'}) RETURN d"}]'
}]->(qSingleIncome);

// Create a finish action
CREATE (actDone:Action {
    actionId: 'ACT_MARK_APPLICANT_INFO_DONE',
    actionType: 'MarkSectionComplete',
    cypher: 'MATCH (app:Application {applicationId:$applicationId}), (s:Section {sectionId:$sectionId}) MERGE (app)-[:COMPLETED]->(s)',
    returnImmediately: true
});

// Connect both paths to the finish action
CREATE (qSecondDOB)-[:TRIGGERS {orderInForm: 4}]->(actDone);
CREATE (qSingleIncome)-[:TRIGGERS {orderInForm: 3}]->(actDone); 