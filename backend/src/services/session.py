import json

from sqlalchemy.orm import create_session

from src.database import get_async_db_connection
from src.config import DATABASE_URL
from src.models.session import UserProfile, AppSession
from src.models.session import TextContent, EvaluationEvidence


class SessionService:
    """
    Service to handle User Sessions.
    Acts as a logical singleton for business logic, but persists state to DB.

    Assumes a table structure roughly like:
    CREATE TABLE sessions (
        session_id SERIAL PRIMARY KEY,
        session_data JSONB NOT NULL
    );
    """

    async def ensure_table_exists(self):
        """
        Idempotent schema initialization.
        Checks if the sessions table exists and creates it if not.
        Call this on application startup (e.g., in FastAPI's @app.on_event("startup")).
        """
        # Postgres-specific syntax (SERIAL, JSONB)
        # Using IF NOT EXISTS avoids race conditions and errors if table is already there.
        if DATABASE_URL is None:
            # SQLite syntax
            query = """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_data TEXT NOT NULL
                );
            """
        else:
            # Postgres syntax
            query = """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id SERIAL PRIMARY KEY,
                    session_data JSONB NOT NULL
                );
            """

        async with get_async_db_connection() as conn:
            cur = await conn.cursor()
            await cur.execute(query)
            await conn.commit()

    async def create_session(self, user_profile: UserProfile = None) -> AppSession:
        """
        Creates a new session in the database.
        """
        # Initialize default empty session structure
        # We temporarily set ID to 0, it will be updated by DB return value
        await self.ensure_table_exists()
        initial_session = AppSession(session_id=0, user_profile=user_profile)

        # We dump the model excluding the ID, as the DB handles the ID
        session_data_json = initial_session.model_dump_json(exclude={'session_id'})

        async with get_async_db_connection() as conn:
            cur = await conn.cursor()
            
            if DATABASE_URL is None:
                # SQLite
                query = "INSERT INTO sessions (session_data) VALUES (?);"
                await cur.execute(query, (session_data_json,))
                # For aiosqlite, lastrowid is available on the cursor after execute
                new_id = cur.lastrowid
            else:
                # Postgres
                query = """
                    INSERT INTO sessions (session_data) 
                    VALUES ($1) 
                    RETURNING session_id;
                """
                await cur.execute(query, (session_data_json,))
                row = await cur.fetchone()
                new_id = row[0]
            
            await conn.commit()

        # Return the complete object with the real ID
        initial_session.session_id = new_id
        return initial_session

    async def get_session(self, session_id: int) -> AppSession | None:
        """
        Retrieves a session by ID. Returns None if not found.
        """
        if DATABASE_URL is None:
            query = "SELECT session_data FROM sessions WHERE session_id = ?;"
        else:
            query = "SELECT session_data FROM sessions WHERE session_id = $1;"

        async with get_async_db_connection() as conn:
            cur = await conn.cursor()
            await cur.execute(query, (session_id,))
            row = await cur.fetchone()

            if not row:
                return None

            data = row[0]
            if isinstance(data, str):
                data = json.loads(data)

            data['session_id'] = session_id

            return AppSession.model_validate(data)

    async def add_text_content(self, session_id: int, content: TextContent) -> AppSession:
        """
        Adds text content to a specific session.
        Note: This uses a Read-Modify-Write pattern.
        """
        async with get_async_db_connection() as conn:
            # 1. Lock the row to prevent race conditions during read-modify-write
            # FOR UPDATE ensures no other worker modifies this row while we are working on it
            if DATABASE_URL is None:
                fetch_query = "SELECT session_data FROM sessions WHERE session_id = ?;"
            else:
                fetch_query = "SELECT session_data FROM sessions WHERE session_id = $1 FOR UPDATE;"

            cur = await conn.cursor()
            await cur.execute(fetch_query, (session_id,))
            row = await cur.fetchone()

            if not row:
                raise ValueError(f"Session {session_id} not found")

            # 2. Deserialize
            data = row[0]
            if isinstance(data, str):
                data = json.loads(data)

            data['session_id'] = session_id  # Ensure ID allows validation
            current_session = AppSession.model_validate(data)

            # 3. Modify
            current_session.text_content_list.append(content)

            # 4. Write back
            # We exclude session_id from storage if the column is separate
            if DATABASE_URL is None:
                update_query = "UPDATE sessions SET session_data = ? WHERE session_id = ?;"
            else:
                update_query = "UPDATE sessions SET session_data = $1 WHERE session_id = $2;"
            new_json = current_session.model_dump_json(exclude={'session_id'})

            await cur.execute(update_query, (new_json, session_id))
            await conn.commit()

            return current_session

    async def add_evidence(self, session_id: int, evidence: EvaluationEvidence) -> AppSession:
        """
        Adds evaluation evidence to a session.
        """
        async with get_async_db_connection() as conn:
            cur = await conn.cursor()

            # 1. Fetch and Lock
            if DATABASE_URL is None:
                await cur.execute("SELECT session_data FROM sessions WHERE session_id = ?;", (session_id,))
            else:
                await cur.execute("SELECT session_data FROM sessions WHERE session_id = $1 FOR UPDATE;", (session_id,))
            
            row = await cur.fetchone()
            if not row:
                raise ValueError(f"Session {session_id} not found")

            data = row[0]
            if isinstance(data, str): data = json.loads(data)
            data['session_id'] = session_id
            current_session = AppSession.model_validate(data)

            # 2. Modify
            current_session.evidence_list.append(evidence)

            # 3. Save
            new_json = current_session.model_dump_json(exclude={'session_id'})
            if DATABASE_URL is None:
                await cur.execute("UPDATE sessions SET session_data = ? WHERE session_id = ?;", (new_json, session_id))
            else:
                await cur.execute("UPDATE sessions SET session_data = $1 WHERE session_id = $2;", (new_json, session_id))
            
            await conn.commit()

            return current_session


# Singleton Instance
# Import this instance in your other files: `from services.session import session_service`
session_service = SessionService()