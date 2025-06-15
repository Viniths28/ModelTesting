# Dynamic Questionnaire System

## Overview
This project is a dynamic questionnaire/loan application system built using FastAPI and Neo4j. It allows for flexible question flow, conditional logic, looping, and integration with dealer-supplied data.

## Key Features
- **Dynamic Question Flow**: Questions are ordered by `sectionOrder` and `order` properties.
- **Conditional Logic**: Questions can be skipped based on `askWhen` conditions, which are evaluated using Neo4j pattern comprehensions.
- **Looping**: Supports looping through questions (e.g., address history).
- **Dealer-Supplied Data**: Integrates with dealer data to pre-fill or skip questions.
- **Action Nodes**: Supports actions like creating co-applicants.

## Project Structure
- **FastAPI**: Handles HTTP requests and responses.
- **Neo4j**: Stores questions, sections, and user responses as nodes and relationships.
- **Ingestion Script**: Loads questions and sections from CSV into Neo4j.
- **Routers**:
  - `seed`: Creates Application and Applicant nodes, and ingests questions.
  - `answer`: Records user responses as Datapoints.
  - `next_question`: Determines the next question based on order and conditions.
  - `trigger_action`: Executes actions like creating co-applicants.

## Logic and Conditions
- **Question Ordering**: Questions are ordered by `sectionOrder` and `order` properties, ensuring a logical flow through the questionnaire.
- **Conditional Logic**: Each question has an `askWhen` property. If `askWhen` is null or empty, the question is always asked. Otherwise, the condition is evaluated using Neo4j pattern comprehensions to check for matching Datapoints. This allows for dynamic question flow based on user responses.
- **Looping**: Questions can loop (e.g., address history) by repeating the same question until a condition is met. For example, if a user indicates they have lived at multiple addresses, the system will repeat the address questions until the user confirms they have no more addresses to add.
- **Branching**: The system supports branching logic (e.g., creating a co-applicant) based on user responses. This allows for complex decision trees and actions to be triggered based on specific answers.
- **Dealer-Supplied Data**: The system integrates with dealer data to pre-fill or skip questions, enhancing the user experience by reducing redundant input.
- **Action Nodes**: Actions like creating co-applicants are supported, allowing the system to dynamically adjust the questionnaire flow based on user actions.

## Approach
- **Ingestion**: Questions and sections are ingested from a CSV file into Neo4j, with `sectionOrder` and `order` properties added.
- **Seeding**: The `seed` endpoint creates Application and Applicant nodes before ingesting questions.
- **Answering**: The `answer` endpoint records user responses as Datapoints.
- **Next Question**: The `next_question` endpoint determines the next question by checking if it's unanswered and if its `askWhen` condition is satisfied.
- **Actions**: The `trigger_action` endpoint executes actions like creating co-applicants.

## Testing
- **Seed Endpoint**: Tested to ensure it creates Application and Applicant nodes and ingests questions correctly.
- **Next Question Endpoint**: Tested to ensure it returns the correct next question based on order and conditions.
- **Full Flow**: Tested the entire flow, including seeding data, answering questions, triggering co-applicant creation, and verifying the next question logic.

## Address Logic
- **Address History**: The system supports looping through address history questions. If a user indicates they have lived at multiple addresses, the system will repeat the address questions until the user confirms they have no more addresses to add.
- **Conditional Checks**: Address questions are skipped if the user indicates they have no previous addresses, based on the `askWhen` condition.

## Conclusion
This system is designed to be flexible and scalable, supporting both static and dynamic conditions, as well as dealer-supplied and user-supplied data. It provides a robust foundation for building dynamic questionnaires and loan applications. 