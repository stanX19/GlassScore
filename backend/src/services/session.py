from src.models.session import UserProfile, AppSession
from src.models.session import TextContent, EvaluationEvidence


class SessionService:
    """
    Service to handle User Sessions.
    Stores sessions in memory using a class variable.
    """
    
    # Class variable to store all sessions in memory
    _sessions: dict[int, AppSession] = {}
    _next_session_id: int = 1

    async def create_session(self, user_profile: UserProfile = None) -> AppSession:
        """
        Creates a new session in memory.
        """
        # Create new session with auto-incrementing ID
        session_id = self._next_session_id
        self._next_session_id += 1
        
        new_session = AppSession(session_id=session_id, user_profile=user_profile)
        self._sessions[session_id] = new_session
        
        return new_session

    async def get_session(self, session_id: int) -> AppSession | None:
        """
        Retrieves a session by ID. Returns None if not found.
        """
        return self._sessions.get(session_id, None)

    async def add_text_content(self, session_id: int, content: TextContent) -> AppSession:
        """
        Adds text content to a specific session.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.text_content_list.append(content)
        return session

    async def add_evidence(self, session_id: int, evidence: EvaluationEvidence) -> AppSession:
        """
        Adds evaluation evidence to a session.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Assign ID
        evidence.id = len(session.evidence_list) + 1
        
        session.evidence_list.append(evidence)
        return session

    async def update_evidence(self, session_id: int, evidence_id: int, valid: bool, invalidate_reason: str) -> AppSession:
        """
        Updates the status of an evidence item.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
            
        for evidence in session.evidence_list:
            if evidence.id == evidence_id:
                evidence.valid = valid
                evidence.invalidate_reason = invalidate_reason
                return session
                
        raise ValueError(f"Evidence {evidence_id} not found in session {session_id}")


# Singleton Instance
# Import this instance in your other files: `from services.session import session_service`
session_service = SessionService()