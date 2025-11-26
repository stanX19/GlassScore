export interface UserProfile {
    name: string;
    age: number;
    gender: string;
    income: number;
    loan_amount: number;
    loan_term: number;
}

export interface TextContent {
    text: string;
    key: string;
    source: string;
}

export interface EvaluationEvidence {
    id: number;
    score: number;
    description: string;
    citation: string;
    source: string;
    valid: boolean;
    invalidate_reason: string;
}

export interface AppSession {
    session_id: number;
    text_content_list: TextContent[];
    evidence_list: EvaluationEvidence[];
    user_profile: UserProfile | null;
}


