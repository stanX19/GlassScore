from datetime import datetime, timedelta
import psycopg2

from langchain.tools import tool
from src.llm.chatbot.tools.tool_context_handler import ToolReg
from src.database import get_async_db_connection


async def _add_medicine_body(
    patient_user_id: int,
    medicine_name: str,
    how_many_times_a_day: int,
    how_many_each_time: int,
    initial_quantity: int | None = None,
    duration: int | None = None,
) -> str:
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=duration) if duration else None
    visit_date = start_date
    dose = f"{how_many_each_time} pills per dose, {how_many_times_a_day}x daily"

    async with get_async_db_connection() as conn:
        async with conn.cursor() as cur:
            # Check for duplicate: same patient, medicine, and start_date
            await cur.execute(
                """
                SELECT record_id FROM medical_record
                WHERE patient_user_id = %s
                  AND LOWER(medicine_name) = LOWER(%s)
                  AND start_date = %s
                """,
                (patient_user_id, medicine_name, start_date)
            )
            existing = await cur.fetchone()

            if existing:
                return f"Error: Medicine '{medicine_name}' already exists in your records with the same start date. Please update the existing record instead."

            try:
                # Insert the new medication
                await cur.execute(
                    """
                    INSERT INTO medical_record (
                        patient_user_id, medicine_name, medical_source, visit_date,
                        dose, start_date, end_date, consent_to_share_publicly,
                        shared_with_primary_doctor, quantity_per_dose, frequency_per_day,
                        initial_quantity, current_quantity
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING record_id
                    """,
                    (
                        patient_user_id, medicine_name, 'patient_reported', visit_date,
                        dose, start_date, end_date, False, False, how_many_each_time, how_many_times_a_day,
                        initial_quantity, initial_quantity
                    )
                )
                result = await cur.fetchone()
                record_id = result["record_id"]
                await conn.commit()

                duration_info = f" for {duration} days (until {end_date})" if duration and end_date else ""
                return f"Medicine '{medicine_name}' successfully added to your medication system. Taking {how_many_each_time} pills, {how_many_times_a_day}x daily{duration_info}"

            except psycopg2.Error as e:
                await conn.rollback()
                if getattr(e, 'pgcode', None) == '23505':  # Unique constraint violation
                    return f"Error: Duplicate medication record detected for '{medicine_name}'"
                raise
            except Exception as e:
                await conn.rollback()
                return f"Error adding medicine: {str(e)}"

def create_add_medicine_tool(patient_user_id: int):
    """
    Factory function that creates an add_medicine tool with patient_user_id bound.
    
    Args:
        patient_user_id: The user ID to bind to the tool
    """

    
    @tool
    @ToolReg.need_confirmation
    async def add_medicine(
        medicine_name: str,
        how_many_times_a_day: int,
        how_many_each_time: int,
        initial_quantity: int | None = None,
        duration: int | None = None,
    ) -> str:
        """
        Adds a new medicine to the patient's medication system.
        Use this when the patient reports starting a new medication.
        
        Args:
            medicine_name: Name of the medicine
            how_many_times_a_day: How often the medicine is taken per day
            how_many_each_time: How many pills to take each time
            initial_quantity: How many pills/doses available initially
            duration: Number of days to take the medicine
        """
        try:
            return await _add_medicine_body(
                patient_user_id,
                medicine_name,
                how_many_times_a_day,
                how_many_each_time,
                initial_quantity,
                duration
            )
        except Exception as e:
            return f"Error adding medicine: {str(e)}"
    
    return add_medicine


# Default instance for backward compatibility (will be replaced by factory in chatbot)
add_medicine = None
