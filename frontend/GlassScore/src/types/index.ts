export interface UserProfile {
    name: string;
    age: number;
    gender: string;
}

export interface LoanApplication {
    person_age: number;
    person_income: number;
    person_home_ownership: 'RENT' | 'OWN' | 'MORTGAGE' | 'OTHER';
    person_emp_length: number;
    loan_intent: 'EDUCATION' | 'MEDICAL' | 'VENTURE' | 'PERSONAL' | 'DEBTCONSOLIDATION' | 'HOMEIMPROVEMENT';
    loan_grade: 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G';
    loan_amnt: number;
    loan_int_rate: number;
    cb_person_default_on_file: 'Y' | 'N';
    cb_person_cred_hist_length: number;
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
    text_content_dict: Record<string, TextContent>;
    evidence_list: EvaluationEvidence[];
    user_profile: UserProfile | null;
    loan_application: LoanApplication | null;
}


