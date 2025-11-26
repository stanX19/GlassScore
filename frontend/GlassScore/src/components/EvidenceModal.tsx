import React, { useState } from 'react';
import type { EvaluationEvidence } from '../types';
import './EvidenceModal.css';

interface EvidenceModalProps {
    evidence: EvaluationEvidence | null;
    isOpen: boolean;
    onClose: () => void;
    onInvalidate: (evidenceId: number, reason: string) => void;
    username: string;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({ 
    evidence, 
    isOpen, 
    onClose, 
    onInvalidate, 
    username 
}) => {
    const [invalidateReason, setInvalidateReason] = useState('');

    if (!isOpen || !evidence) return null;

    const handleInvalidate = () => {
        if (invalidateReason.trim()) {
            const timestamp = new Date().toLocaleString();
            const formattedReason = `Invalidated by user ${username} at ${timestamp}. Reason: ${invalidateReason}`;
            onInvalidate(evidence.id, formattedReason);
            setInvalidateReason('');
            onClose();
        }
    };

    const handleOverlayClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    return (
        <div className="modal-overlay" onClick={handleOverlayClick}>
            <div className="modal-content">
                <div className="modal-header">
                    <h3>Evidence Details</h3>
                    <button className="modal-close" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {!evidence.valid && (
                        <div className="invalid-notice">
                            <strong>⚠️ This evidence has been invalidated</strong>
                            <p>{evidence.invalidate_reason}</p>
                        </div>
                    )}

                    <div className="modal-section">
                        <h4>Score</h4>
                        <p style={{ fontWeight: 'bold', fontSize: '1.25rem' }}>
                            {evidence.score > 0 ? '+' : ''}{evidence.score}
                        </p>
                    </div>

                    <div className="modal-section">
                        <h4>Description</h4>
                        <p>{evidence.description}</p>
                    </div>

                    <div className="modal-section">
                        <h4>Citation</h4>
                        <div className="citation-box">{evidence.citation}</div>
                    </div>

                    <div className="modal-section">
                        <h4>Source</h4>
                        <p>{evidence.source}</p>
                    </div>

                    {evidence.valid && (
                        <div className="invalidate-section">
                            <h4>Invalidate Evidence</h4>
                            <textarea
                                value={invalidateReason}
                                onChange={(e) => setInvalidateReason(e.target.value)}
                                placeholder="Enter reason for invalidation..."
                                rows={3}
                            />
                            <button 
                                onClick={handleInvalidate}
                                disabled={!invalidateReason.trim()}
                                className="btn-invalidate"
                            >
                                Invalidate Evidence
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
