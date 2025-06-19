// Create main section for dealer information
CREATE (secDealer:Section {
    sectionId: 'SEC_DEALER_INFO',
    name: 'Dealer Information',
    inputParams: ['applicationId', 'applicantId']
});

// Create the initial dealer address question
CREATE (qHasDealer:Question {
    questionId: 'Q_HAS_DEALER',
    prompt: 'Do you want to enter dealer address?',
    fieldId: 'F_HAS_DEALER',
    dataType: 'boolean',
    exampleAnswer: 'yes/no',
    orderInForm: 1
});

// Create questions for Yes path (dealer address collection)
CREATE (qDealerName:Question {
    questionId: 'Q_DEALER_NAME',
    prompt: 'What is the dealer name?',
    fieldId: 'F_DEALER_NAME',
    dataType: 'string',
    orderInForm: 2
});

CREATE (qDealerStreet:Question {
    questionId: 'Q_DEALER_STREET',
    prompt: 'What is the dealer street address?',
    fieldId: 'F_DEALER_STREET',
    dataType: 'string',
    orderInForm: 3
});

CREATE (qDealerCity:Question {
    questionId: 'Q_DEALER_CITY',
    prompt: 'What is the dealer city?',
    fieldId: 'F_DEALER_CITY',
    dataType: 'string',
    orderInForm: 4
});

CREATE (qDealerState:Question {
    questionId: 'Q_DEALER_STATE',
    prompt: 'What is the dealer state?',
    fieldId: 'F_DEALER_STATE',
    dataType: 'string',
    orderInForm: 5
});

CREATE (qDealerPostcode:Question {
    questionId: 'Q_DEALER_POSTCODE',
    prompt: 'What is the dealer postcode?',
    fieldId: 'F_DEALER_POSTCODE',
    dataType: 'string',
    orderInForm: 6
});

// Create a property creation action for dealer address
CREATE (actCreateDealer:Action {
    actionId: 'ACT_CREATE_DEALER_PROPERTY',
    actionType: 'CreatePropertyNode',
    cypher: 'MATCH (app:Application {applicationId:$applicationId}) 
            WITH app
            MATCH (src)-[:SUPPLIES]->(dName:Datapoint)-[:ANSWERS]->(q:Question {questionId:"Q_DEALER_NAME"}),
                  (src)-[:SUPPLIES]->(dStreet:Datapoint)-[:ANSWERS]->(q2:Question {questionId:"Q_DEALER_STREET"}),
                  (src)-[:SUPPLIES]->(dCity:Datapoint)-[:ANSWERS]->(q3:Question {questionId:"Q_DEALER_CITY"}),
                  (src)-[:SUPPLIES]->(dState:Datapoint)-[:ANSWERS]->(q4:Question {questionId:"Q_DEALER_STATE"}),
                  (src)-[:SUPPLIES]->(dPostcode:Datapoint)-[:ANSWERS]->(q5:Question {questionId:"Q_DEALER_POSTCODE"})
            CREATE (app)-[:HAS_DEALER_ADDRESS]->(dealer:DealerAddress {
                name: dName.value,
                street: dStreet.value,
                city: dCity.value,
                state: dState.value,
                postcode: dPostcode.value,
                createdBy: "engine"
            })
            RETURN id(dealer) as createdId',
    returnImmediately: true
});

// Create finish action
CREATE (actDone:Action {
    actionId: 'ACT_MARK_DEALER_INFO_DONE',
    actionType: 'MarkSectionComplete',
    cypher: 'MATCH (app:Application {applicationId:$applicationId}), (s:Section {sectionId:$sectionId}) MERGE (app)-[:COMPLETED]->(s)',
    returnImmediately: true
});

// Create relationships with proper askWhen conditions

// Initial question connection
CREATE (secDealer)-[:PRECEDES {
    orderInForm: 1,
    sourceNode: 'cypher: MATCH (app:Application {applicationId:$applicationId})-[:HAS_APPLICANT]->(a:Applicant {applicantId:$applicantId}) RETURN a'
}]->(qHasDealer);

// Yes path - Dealer address questions with dependencies
CREATE (qHasDealer)-[:PRECEDES {
    orderInForm: 2,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"yes"})-[:ANSWERS]->(q:Question {questionId:"Q_HAS_DEALER"}) RETURN d',
    variables: '[{"name":"has_dealer_answer","cypher":"MATCH (src)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId:\'Q_HAS_DEALER\'}) RETURN d"}]'
}]->(qDealerName);

CREATE (qDealerName)-[:PRECEDES {
    orderInForm: 3,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"yes"})-[:ANSWERS]->(q:Question {questionId:"Q_HAS_DEALER"}) RETURN d'
}]->(qDealerStreet);

CREATE (qDealerStreet)-[:PRECEDES {
    orderInForm: 4,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"yes"})-[:ANSWERS]->(q:Question {questionId:"Q_HAS_DEALER"}) RETURN d'
}]->(qDealerCity);

CREATE (qDealerCity)-[:PRECEDES {
    orderInForm: 5,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"yes"})-[:ANSWERS]->(q:Question {questionId:"Q_HAS_DEALER"}) RETURN d'
}]->(qDealerState);

CREATE (qDealerState)-[:PRECEDES {
    orderInForm: 6,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"yes"})-[:ANSWERS]->(q:Question {questionId:"Q_HAS_DEALER"}) RETURN d'
}]->(qDealerPostcode);

// Connect dealer address collection to property creation action
CREATE (qDealerPostcode)-[:TRIGGERS {
    orderInForm: 7,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"yes"})-[:ANSWERS]->(q:Question {questionId:"Q_HAS_DEALER"}) RETURN d'
}]->(actCreateDealer);

// Connect property creation to section completion
CREATE (actCreateDealer)-[:TRIGGERS {orderInForm: 8}]->(actDone);

// No path - Direct to completion if no dealer address needed
CREATE (qHasDealer)-[:TRIGGERS {
    orderInForm: 2,
    askWhen: 'cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint {value:"no"})-[:ANSWERS]->(q:Question {questionId:"Q_HAS_DEALER"}) RETURN d'
}]->(actDone); 