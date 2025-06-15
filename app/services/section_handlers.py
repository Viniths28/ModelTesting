from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from neo4j import AsyncGraphDatabase

class SectionHandler(ABC):
    @abstractmethod
    async def get_next_question(self, 
                              section_id: str, 
                              applicant_id: str, 
                              application_id: str,
                              driver: AsyncGraphDatabase) -> Optional[Dict[str, Any]]:
        pass

class LivingSituationHandler(SectionHandler):
    async def get_next_question(self, section_id: str, applicant_id: str, application_id: str, driver: AsyncGraphDatabase):
        async with driver.session() as session:
            # Check for address datapoint
            address_check = await session.run(
                """
                MATCH (a:Applicant {applicantId: $applicantId})-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: 'Q_AD_Residential_Address_(CustomerCurrent)'})
                RETURN d
                """,
                {"applicantId": applicant_id}
            )
            address_datapoint = await address_check.single()
            
            if address_datapoint:
                # Handle address check flow
                address_check_question = await session.run(
                    """
                    MATCH (a:Applicant {applicantId: $applicantId})-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q:Question {questionId: 'Q_AD_AddressCheck'})
                    RETURN d
                    """,
                    {"applicantId": applicant_id}
                )
                address_check_answer = await address_check_question.single()
                
                if not address_check_answer:
                    return {"questionId": "Q_AD_AddressCheck", "questionText": "Is this address correct?"}
                elif address_check_answer["d"]["typedValue"] == "No":
                    return {"questionId": "Q_AD_Residential_Address_(CustomerCurrent)", "questionText": "What is your current residential address?"}
            
            # If no special handling needed, return None to use default flow
            return None

class DefaultSectionHandler(SectionHandler):
    async def get_next_question(self, section_id: str, applicant_id: str, application_id: str, driver: AsyncGraphDatabase):
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (sec:Section {sectionId: $sectionId})
                MATCH path=(sec)-[:PRECEDES*]->(q:Question)
                WITH q, path, relationships(path) as rels
                WHERE NOT (q)<-[:ANSWERS]-(:Datapoint)<-[:SUPPLIES]-(:Applicant {applicantId: $applicantId})
                WITH q, rels
                ORDER BY q.sectionOrder ASC
                WITH q, head(rels) as rel
                WHERE rel.askWhen IS NULL 
                   OR rel.askWhen = '' 
                   OR size([(a:Applicant {applicantId: $applicantId})-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q2:Question)
                           WHERE q2.questionId = split(rel.askWhen, '=')[0] 
                           AND d.typedValue = split(rel.askWhen, '=')[1] | 1]) > 0
                RETURN q
                LIMIT 1
                """,
                {
                    "sectionId": section_id,
                    "applicantId": applicant_id,
                    "applicationId": application_id
                }
            )
            record = await result.single()
            return record["q"] if record else None

# Factory to get the appropriate handler
class SectionHandlerFactory:
    _handlers = {
        "Living Situation": LivingSituationHandler(),
        # Add more section handlers here as needed
    }

    @classmethod
    def get_handler(cls, section_id: str) -> SectionHandler:
        return cls._handlers.get(section_id, DefaultSectionHandler()) 