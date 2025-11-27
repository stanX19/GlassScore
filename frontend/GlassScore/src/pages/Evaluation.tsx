import React, { useEffect, useState, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiService } from '../utils/api';
import type { EvaluationEvidence, AppSession } from '../types';
import { EvidenceCard } from '../components/EvidenceCard';
import { EvidenceModal } from '../components/EvidenceModal';
import { ScoreBar } from '../components/ScoreBar';
import './Evaluation.css';

export const Evaluation: React.FC = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const sessionId = location.state?.sessionId;
    const profileName = location.state?.profileName || 'Unknown';
    const [evidences, setEvidences] = useState<EvaluationEvidence[]>([]);
    const [selectedEvidence, setSelectedEvidence] = useState<EvaluationEvidence | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [totalScore, setTotalScore] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [session, setSession] = useState<AppSession | null>(null);
    const streamInitiatedRef = useRef(false);
    const [isApproved, setIsApproved] = useState<boolean | null>(null);
    const [isOverride, setIsOverride] = useState(false);
    const [showRiskModal, setShowRiskModal] = useState(false);

    const username = localStorage.getItem('glassscore_username') || 'Unknown User';

    useEffect(() => {
        // Check if user has a username (not new user)
        if (!username || username === 'Unknown User') {
            navigate('/');
            return;
        }

        if (!sessionId) {
            navigate('/data-fill');
            return;
        }

        // Reset stream flag for new session
        streamInitiatedRef.current = false;

        const initSession = async () => {
            try {
                // First, try to fetch existing session data
                const sessionData = await apiService.getSession(sessionId);
                setSession(sessionData); // Store session for text content access
                if (sessionData.evidence_list && sessionData.evidence_list.length > 0) {
                    // Evidence already exists, display it
                    setEvidences(sessionData.evidence_list);
                    // If we have evidence, we might still want to listen for updates if the evaluation isn't "complete"
                    // But for now, let's assume if we load from DB, we just show it.
                    // However, to support re-evaluation after page reload, we should probably connect to stream anyway?
                    // The backend says "Stream stays open indefinitely".
                    // So we should probably always connect to stream to get updates.
                    // But we don't want to duplicate evidence.
                    // Let's connect to stream but be careful about duplicates.
                }
            } catch (error) {
                console.error('Failed to fetch existing session:', error);
            }

            // Always start streaming to catch new events or re-evaluations
            if (streamInitiatedRef.current) {
                return;
            }
            streamInitiatedRef.current = true;
            
            const fetchStream = async () => {
                try {
                    const response = await fetch(apiService.getStreamUrl(), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ session_id: sessionId }),
                    });

                    if (!response.body) {
                        setIsLoading(false);
                        return;
                    }
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) {
                            // Stream closed unexpectedly (network issue?) or server closed it
                            console.log('Stream closed');
                            break;
                        }
                        
                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\n');
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    
                                    if (data.event_type === 'evaluation_start') {
                                        console.log('Evaluation started');
                                        setIsLoading(true);
                                    } else if (data.event_type === 'evaluation_complete') {
                                        console.log('Initial evaluation completed');
                                        setIsLoading(false);
                                        // Do NOT close the stream, keep listening for re-evaluations
                                    } else if (data.event_type === 'evidence' || !data.event_type) {
                                        // Handle evidence
                                        setEvidences(prev => {
                                            // Check if evidence with this ID already exists
                                            const existingIndex = prev.findIndex(e => e.id === data.id);
                                            if (existingIndex >= 0) {
                                                // Update existing evidence (e.g. if it was modified)
                                                // But wait, re-evaluation creates NEW evidence with NEW ID.
                                                // So we shouldn't need to update existing ones usually, unless the backend updates them in place?
                                                // The backend says: "Original evidence remains in the list (not replaced)"
                                                // "New evidence is pushed... Gets new id"
                                                // So we just add it.
                                                // However, we should avoid duplicates if we re-connected.
                                                return prev;
                                            }
                                            return [...prev, data];
                                        });
                                        
                                        // If we receive evidence, we are definitely not "loading" anymore in terms of "empty state"
                                        // But we might still be "evaluating".
                                        // Let's keep isLoading true until evaluation_complete OR we have some evidence?
                                        // Actually, if we have evidence, we can show it.
                                    }
                                } catch (e) {
                                    console.error('Error parsing SSE data:', e);
                                }
                            }
                        }
                    }
                } catch (error) {
                    console.error('Stream error:', error);
                    setIsLoading(false);
                }
            };

            fetchStream();
        };

        initSession();
    }, [sessionId, username]);

    // Recalculate score whenever evidences change
    useEffect(() => {
        const score = evidences.reduce((acc, curr) => {
            return curr.valid ? acc + curr.score : acc;
        }, 0);
        setTotalScore(score);
    }, [evidences]);

    const handleEvidenceClick = (evidence: EvaluationEvidence) => {
        setSelectedEvidence(evidence);
        setIsModalOpen(true);
    };

    const handleInvalidate = async (evidenceId: number, reason: string) => {
        try {
            if (!sessionId) return;
            
            // Optimistic update
            setEvidences(prev => prev.map(e => 
                e.id === evidenceId ? { ...e, valid: false, invalidate_reason: reason } : e
            ));

            // API call
            await apiService.updateEvidence(sessionId, evidenceId, false, reason);
            
            // Update selected evidence if modal is open
            if (selectedEvidence?.id === evidenceId) {
                setSelectedEvidence(prev => prev ? { ...prev, valid: false, invalidate_reason: reason } : null);
            }
        } catch (error) {
            console.error('Failed to invalidate evidence:', error);
        }
    };

    const handleUndo = async (evidenceId: number) => {
        try {
            if (!sessionId) return;
            
            // Optimistic update
            setEvidences(prev => prev.map(e => 
                e.id === evidenceId ? { ...e, valid: true, invalidate_reason: '' } : e
            ));

            // API call
            await apiService.updateEvidence(sessionId, evidenceId, true, '');
            
            // Update selected evidence if modal is open
            if (selectedEvidence?.id === evidenceId) {
                setSelectedEvidence(prev => prev ? { ...prev, valid: true, invalidate_reason: '' } : null);
            }
        } catch (error) {
            console.error('Failed to undo invalidation:', error);
        }
    };

    const handleAccept = () => {
        setIsApproved(true);
        setIsOverride(false);
    };

    const handleApproveAnyway = () => {
        setShowRiskModal(true);
    };

    const handleConfirmRiskApproval = () => {
        setIsApproved(true);
        setIsOverride(true);
        setShowRiskModal(false);
    };

    const handleCancelRiskApproval = () => {
        setShowRiskModal(false);
    };

    // Separate and sort evidences by magnitude first, then by ID (newer first)
    const sortByMagnitudeAndTime = (a: EvaluationEvidence, b: EvaluationEvidence) => {
        const magA = Math.abs(a.score);
        const magB = Math.abs(b.score);
        if (magB !== magA) return magB - magA; // Higher magnitude first
        return b.id - a.id; // Newer (higher ID) first as tiebreaker
    };
    
    const validEvidences = evidences.filter(e => e.valid);
    const invalidatedEvidences = evidences.filter(e => !e.valid);
    
    // Positives: score > 0
    const positives = validEvidences.filter(e => e.score > 0).sort(sortByMagnitudeAndTime);
    // Zeros and negatives: score <= 0
    const zerosAndNegatives = validEvidences.filter(e => e.score <= 0).sort(sortByMagnitudeAndTime);
    
    // Split invalidated by original score
    const invalidatedPositives = invalidatedEvidences.filter(e => e.score > 0).sort(sortByMagnitudeAndTime);
    const invalidatedZerosNegatives = invalidatedEvidences.filter(e => e.score <= 0).sort(sortByMagnitudeAndTime);
    
    // Helper to determine if an evidence should be wide (only first eligible one in each category)
    const shouldBeWide = (evidence: EvaluationEvidence, list: EvaluationEvidence[]) => {
        const threshold = evidence.score > 0 ? 10 : -10;
        const isEligible = evidence.score > 0 ? evidence.score >= threshold : evidence.score <= threshold;
        if (!isEligible) return false;
        // Check if this is the first eligible one in the list
        const firstEligibleIndex = list.findIndex(e => 
            e.score > 0 ? e.score >= 10 : e.score <= -10
        );
        return list[firstEligibleIndex]?.id === evidence.id;
    };

    return (
        <div className="evaluation-container">
            {/* Header */}
            <header className="evaluation-header">
                <div className="evaluation-header-content">
                    <h1>Evaluating: {profileName}</h1>
                    <div className="evaluation-header-buttons">
                        <button onClick={() => navigate('/data-fill')} className="btn-back">
                            Back
                        </button>
                        <button onClick={() => navigate('/data-fill')} className="btn-evaluate-another">
                            Evaluate Another User
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="evaluation-main">
                {isLoading && evidences.length === 0 ? (
                    <div className="evaluation-loading">
                        <div className="spinner"></div>
                        <p>Waiting for evidence stream...</p>
                    </div>
                ) : evidences.length === 0 ? (
                    <div className="evaluation-loading">
                        <p>No evidence found. The evaluation may have completed already.</p>
                    </div>
                ) : (
                    <>
                        {/* Two separate 2-column grids side by side */}
                        <div className="evidence-grid-wrapper">
                            {/* Left side: Positive scores (2 columns) */}
                            <div className="evidence-grid-section">
                                {/* Valid positives */}
                                {positives.map((evidence) => (
                                    <EvidenceCard 
                                        key={evidence.id} 
                                        evidence={evidence} 
                                        onClick={() => handleEvidenceClick(evidence)} 
                                        badge={evidence.source.startsWith('Re-evaluation of Evidence #') ? 'Re-evaluated' : undefined}
                                        isWide={shouldBeWide(evidence, positives)}
                                    />
                                ))}
                                
                                {/* Invalidated positives */}
                                {invalidatedPositives.map((evidence) => (
                                    <EvidenceCard 
                                        key={evidence.id} 
                                        evidence={evidence} 
                                        onClick={() => handleEvidenceClick(evidence)} 
                                        badge={evidence.source.startsWith('Re-evaluation of Evidence #') ? 'Re-evaluated' : undefined}
                                        isWide={shouldBeWide(evidence, invalidatedPositives)}
                                    />
                                ))}
                            </div>

                            {/* Right side: Negative/Neutral scores (2 columns) */}
                            <div className="evidence-grid-section">
                                {/* Valid negatives */}
                                {zerosAndNegatives.map((evidence) => (
                                    <EvidenceCard 
                                        key={evidence.id} 
                                        evidence={evidence} 
                                        onClick={() => handleEvidenceClick(evidence)} 
                                        badge={evidence.source.startsWith('Re-evaluation of Evidence #') ? 'Re-evaluated' : undefined}
                                        isWide={shouldBeWide(evidence, zerosAndNegatives)}
                                    />
                                ))}

                                {/* Invalidated negatives */}
                                {invalidatedZerosNegatives.map((evidence) => (
                                    <EvidenceCard 
                                        key={evidence.id} 
                                        evidence={evidence} 
                                        onClick={() => handleEvidenceClick(evidence)} 
                                        badge={evidence.source.startsWith('Re-evaluation of Evidence #') ? 'Re-evaluated' : undefined}
                                        isWide={shouldBeWide(evidence, invalidatedZerosNegatives)}
                                    />
                                ))}
                            </div>
                        </div>
                    </>
                )}
            </main>

            {/* Bottom Score Bar */}
            <footer className="score-bar-footer">
                <div className="score-bar-content-horizontal">
                    <ScoreBar score={totalScore} />
                    {isLoading ? (
                        <div className="loading-indicator">
                            <div className="spinner-small"></div>
                        </div>
                    ) : (
                        <div className="checkmark-horizontal">✓</div>
                    )}
                    <div className="verdict-text">
                        {isApproved && isOverride ? (
                            <>Approved (Overridden by {username})</>
                        ) : (
                            <>Final verdict: {totalScore >= 50 ? 'Approve Loan' : 'Reject Loan'}</>
                        )}
                    </div>
                    {isApproved !== null ? (
                        <button className="btn-approved" disabled>
                            Loan Approved ✓
                        </button>
                    ) : totalScore >= 50 ? (
                        <button className="btn-accept" onClick={handleAccept}>
                            Accept
                        </button>
                    ) : (
                        <button className="btn-approve-anyway" onClick={handleApproveAnyway}>
                            Approve Anyway
                        </button>
                    )}
                </div>
            </footer>

            {/* Risk Approval Modal */}
            {showRiskModal && (
                <div className="risk-modal-overlay" onClick={handleCancelRiskApproval}>
                    <div className="risk-modal" onClick={(e) => e.stopPropagation()}>
                        <h2>Are you sure?</h2>
                        <p className="risk-warning">High risk loan</p>
                        <div className="risk-modal-buttons">
                            <button className="btn-cancel" onClick={handleCancelRiskApproval}>
                                Cancel
                            </button>
                            <button className="btn-confirm" onClick={handleConfirmRiskApproval}>
                                Confirm
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal */}
            <EvidenceModal 
                evidence={selectedEvidence}
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onInvalidate={handleInvalidate}
                onUndo={handleUndo}
                username={username}
                session={session}
            />
        </div>
    );
};
