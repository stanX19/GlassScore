import axios from 'axios';
import { BASE_URL } from './constants';
import type { UserProfile, LoanApplication, TextContent, AppSession } from '../types';

const API_BASE_URL = BASE_URL;

class ApiService {
    async createSession(): Promise<AppSession> {
        const response = await axios.post(`${API_BASE_URL}/session/create`);
        return response.data;
    }

    async updateProfile(sessionId: number, userProfile: UserProfile, loanApplication: LoanApplication): Promise<AppSession> {
        const response = await axios.post(`${API_BASE_URL}/session/update`, {
            session_id: sessionId,
            user_profile: userProfile,
            loan_application: loanApplication
        });
        return response.data;
    }

    async attachContent(sessionId: number, textContent: TextContent): Promise<AppSession> {
        const response = await axios.post(`${API_BASE_URL}/session/attach`, {
            session_id: sessionId,
            text_content: textContent
        });
        return response.data;
    }

    async updateEvidence(sessionId: number, evidenceId: number, valid: boolean, invalidateReason: string): Promise<AppSession> {
        const response = await axios.post(`${API_BASE_URL}/evaluate/evidence/update`, {
            session_id: sessionId,
            evidence_id: evidenceId,
            valid: valid,
            invalidate_reason: invalidateReason
        });
        return response.data;
    }

    async getSession(sessionId: number): Promise<AppSession> {
        const response = await axios.get(`${API_BASE_URL}/session/get`, {
            params: { session_id: sessionId }
        });
        return response.data;
    }

    getStreamUrl(): string {
        return `${API_BASE_URL}/evaluate/stream`;
    }

    async startEvaluation(sessionId: number): Promise<void> {
        await axios.post(`${API_BASE_URL}/evaluate/start`, {
            session_id: sessionId
        });
    }
}

export const apiService = new ApiService();