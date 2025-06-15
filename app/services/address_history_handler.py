# app/services/address_history_handler.py

from typing import Optional, Dict, Any
from neo4j import AsyncGraphDatabase
from datetime import datetime, timedelta

class AddressHistoryHandler:
    @staticmethod
    async def handle_address_history(
        driver: AsyncGraphDatabase,
        applicant_id: str,
        question_id: str,
        value: str
    ) -> Optional[Dict[str, Any]]:
        """
        Always prompt for address first, then start date, for both current and prior addresses.
        """
        async with driver.session() as session:
            # 1. Handle current address
            if question_id == "Q_AD_Residential_Address_(CustomerCurrent)":
                # Save current address as a datapoint
                # Next: ask for current start date
                return {
                    "nextQuestion": {
                        "questionId": "Q_AD_Residential_Start_Date_(Customer)",
                        "questionText": "When did you start living at this address?"
                    }
                }

            # 2. Handle current start date
            elif question_id == "Q_AD_Residential_Start_Date_(Customer)":
                # Save current start date as a datapoint
                # Next: ask for prior address
                return {
                    "nextQuestion": {
                        "questionId": "Q_AD_Residential_Address_(CustomerPrior)",
                        "questionText": "What was your previous address?"
                    }
                }

            # 3. Handle prior address (create AddressHistory node)
            elif question_id == "Q_AD_Residential_Address_(CustomerPrior)":
                # Create AddressHistory node and save prior address
                await session.run(
                    """
                    MATCH (a:Applicant {applicantId: $applicantId})
                    CREATE (ah:AddressHistory {
                        addressHistoryId: apoc.create.uuid(),
                        createdAt: datetime(),
                        priorAddress: $value
                    })
                    CREATE (a)-[:HAS_ADDRESS_HISTORY]->(ah)
                    """,
                    {
                        "applicantId": applicant_id,
                        "value": value
                    }
                )
                # Next: ask for start date for this prior address
                return {
                    "nextQuestion": {
                        "questionId": "Q_AD_Residential_Start_Date_(Customer)",
                        "questionText": "When did you start living at this prior address?"
                    }
                }

            # 4. Handle prior start date (update latest AddressHistory)
            elif question_id == "Q_AD_Residential_Start_Date_(Customer)":
                # Update the latest AddressHistory node with start date
                await session.run(
                    """
                    MATCH (a:Applicant {applicantId: $applicantId})-[:HAS_ADDRESS_HISTORY]->(ah:AddressHistory)
                    WHERE NOT EXISTS(ah.priorStartDate)
                    SET ah.priorStartDate = $value
                    """,
                    {
                        "applicantId": applicant_id,
                        "value": value
                    }
                )
                # Now check if we need more history (sum durations)
                result = await session.run(
                    """
                    MATCH (a:Applicant {applicantId: $applicantId})-[:HAS_ADDRESS_HISTORY]->(ah:AddressHistory)
                    WITH ah
                    WHERE EXISTS(ah.priorStartDate)
                    WITH collect(ah) as histories
                    WITH reduce(total = 0, h in histories | 
                        total + duration.between(datetime(h.priorStartDate), datetime(h.createdAt)).days
                    ) as totalDays
                    RETURN totalDays
                    """,
                    {"applicantId": applicant_id}
                )
                record = await result.single()
                if record and record["totalDays"] < 730:  # Less than 24 months
                    # Need more address history
                    return {
                        "nextQuestion": {
                            "questionId": "Q_AD_Residential_Address_(CustomerPrior)",
                            "questionText": "What was your previous address?"
                        }
                    }
                else:
                    # Have enough address history, continue with next section question
                    return None

        return None