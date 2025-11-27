from src.models.ml_model import LoanApplication
from src.models.session import UserProfile, AppSession
from src.models.session import TextContent, EvaluationEvidence
import asyncio


class SessionService:
    """
    Service to handle User Sessions.
    Stores sessions in memory using a class variable.
    """
    
    # Class variable to store all sessions in memory
    _sessions: dict[int, AppSession] = {}
    _next_session_id: int = 1
    async def create_session(self, user_profile: UserProfile = None, loan_application: LoanApplication = None) -> AppSession:
        """
        Creates a new session in memory.
        """
        # Create new session with auto-incrementing ID
        session_id = self._next_session_id
        self._next_session_id += 1
        
        new_session = AppSession(
            session_id=session_id,
            user_profile=user_profile,
            loan_application=loan_application,
            evidence_queue=asyncio.Queue()
        )
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
        
        session.text_content_dict[content.key] = content
        return session

    async def save_text_content(self, session_id: int, content: TextContent) -> str:
        """
        Saves text content to session, ensuring unique keys by appending suffixes if needed.
        Returns the final key used (which may differ from content.key if duplicates exist).
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Check for key conflicts and append suffix if needed
        original_key = content.key
        final_key = original_key
        counter = 1
        
        while final_key in session.text_content_dict:
            final_key = f"{original_key}_{counter}"
            counter += 1
        
        # Update content key if it was changed
        if final_key != original_key:
            content.key = final_key
        
        # Save to dict
        session.text_content_dict[final_key] = content
        
        return final_key

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

    async def push_evidence_to_stream(self, session_id: int, evidence: EvaluationEvidence) -> None:
        """
        Push evidence to the session's queue for streaming.
        This allows dynamic addition of evidence during evaluation.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.evidence_queue:
            await session.evidence_queue.put(evidence)

    async def start_evaluation(self, session_id: int) -> None:
        """
        Mark session as evaluating and initialize queue if needed.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.is_evaluating = True
        if session.evidence_queue is None:
            session.evidence_queue = asyncio.Queue()

    async def finish_evaluation(self, session_id: int) -> None:
        """
        Mark session evaluation as complete.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.is_evaluating = False
        session.pending_tasks = 0

    async def update_evidence(self, session_id: int, evidence_id: int, valid: bool, invalidate_reason: str) -> AppSession:
        """
        Updates the status of an evidence item.
        If marking as invalid, triggers re-evaluation via LLM.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
            
        for evidence in session.evidence_list:
            if evidence.id == evidence_id:
                evidence.valid = valid
                evidence.invalidate_reason = invalidate_reason
                
                # If invalidated, trigger re-evaluation
                if not valid:
                    asyncio.create_task(self._reevaluate_invalidated_evidence(session_id, evidence))
                
                return session
                
        raise ValueError(f"Evidence {evidence_id} not found in session {session_id}")

    async def _reevaluate_invalidated_evidence(self, session_id: int, original_evidence: EvaluationEvidence) -> None:
        """
        Re-evaluate invalidated evidence using LLM analysis.
        Pushes new evidence to stream without replacing the original.
        """
        from src.services.evaluation.reevaluate_invalidated import reevaluate_invalidated_evidence
        
        session = self._sessions.get(session_id)
        if not session:
            return
        
        try:
            # Use the new re-evaluation service
            new_evidence_list = await reevaluate_invalidated_evidence(session, original_evidence)
            
            # Push all new evidence to stream
            for new_evidence in new_evidence_list:
                await self.push_evidence_to_stream(session_id, new_evidence)
                
        except Exception as e:
            # Push error evidence
            error_evidence = EvaluationEvidence(
                score=0,
                description=f"Failed to re-evaluate evidence #{original_evidence.id}: {str(e)}",
                citation="",
                source="Re-evaluation Error",
                text_content_key=None
            )
            await self.push_evidence_to_stream(session_id, error_evidence)


# Singleton Instance
# Import this instance in your other files: `from services.session import session_service`
session_service = SessionService()