import React from 'react';
import type { EvaluationEvidence } from '../types';
import { COLORS } from '../utils/color';
import './EvidenceCard.css';

interface EvidenceCardProps {
    evidence: EvaluationEvidence;
    onClick: () => void;
    badge?: string;
    isWide?: boolean;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ evidence, onClick, badge, isWide }) => {
    const getScoreClass = () => {
        if (evidence.score > 0) return 'positive';
        if (evidence.score < 0) return 'negative';
        return 'neutral';
    };

    const isUrl = (str: string) => {
        try {
            new URL(str);
            return true;
        } catch {
            return false;
        }
    };

    const handleSourceClick = (e: React.MouseEvent) => {
        e.stopPropagation();
    };

    const scoreClass = getScoreClass();
    const cardClass = `evidence-card ${scoreClass} ${!evidence.valid ? 'invalid' : ''} ${isWide ? 'wide' : ''}`;

    return (
        <div className={cardClass} onClick={onClick}>
            <div className={`evidence-score ${scoreClass}`}>
                {evidence.score > 0 ? '+' : ''}{evidence.score}
            </div>
            <p className="evidence-description">
                {evidence.description}
            </p>
			{/* {evidence.citation && (
				<span className="evidence-citation-inline"> "{evidence.citation}"</span>
			)} */}
            <p className="evidence-source">
                Source: {isUrl(evidence.source) ? (
                    <a 
                        href={evidence.source} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        onClick={handleSourceClick}
                        style={{ color: COLORS.BLUE, textDecoration: 'underline' }}
                    >
                        {evidence.source}
                    </a>
                ) : evidence.source}
            </p>
            {!evidence.valid && (
                <div className="evidence-invalid-badge">INVALIDATED</div>
            )}
            {badge && (
                <div className="evidence-badge">{badge}</div>
            )}
        </div>
    );
};
