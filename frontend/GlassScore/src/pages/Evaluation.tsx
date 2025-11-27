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

    // Separate and sort evidences
    const validEvidences = evidences.filter(e => e.valid);
    const invalidatedEvidences = evidences.filter(e => !e.valid);
    
    // Positives: score > 0
    const positives = validEvidences.filter(e => e.score > 0).sort((a, b) => b.score - a.score);
    // Zeros and negatives: score <= 0
    const zerosAndNegatives = validEvidences.filter(e => e.score <= 0).sort((a, b) => b.score - a.score);
    
    // Split invalidated by original score
    const invalidatedPositives = invalidatedEvidences.filter(e => e.score > 0).sort((a, b) => b.score - a.score);
    const invalidatedZerosNegatives = invalidatedEvidences.filter(e => e.score <= 0).sort((a, b) => b.score - a.score);

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

            {/* Main Layout with Score Bar on Right */}
            <div className="evaluation-layout">
                <main className="evaluation-main-with-sidebar">
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
                                            isWide={evidence.score >= 10}
                                        />
                                    ))}
                                    
                                    {/* Invalidated positives */}
                                    {invalidatedPositives.map((evidence) => (
                                        <EvidenceCard 
                                            key={evidence.id} 
                                            evidence={evidence} 
                                            onClick={() => handleEvidenceClick(evidence)} 
                                            badge={evidence.source.startsWith('Re-evaluation of Evidence #') ? 'Re-evaluated' : undefined}
                                            isWide={evidence.score >= 10}
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
                                            isWide={evidence.score <= -20}
                                        />
                                    ))}

                                    {/* Invalidated negatives */}
                                    {invalidatedZerosNegatives.map((evidence) => (
                                        <EvidenceCard 
                                            key={evidence.id} 
                                            evidence={evidence} 
                                            onClick={() => handleEvidenceClick(evidence)} 
                                            badge={evidence.source.startsWith('Re-evaluation of Evidence #') ? 'Re-evaluated' : undefined}
                                            isWide={evidence.score <= -20}
                                        />
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </main>

                {/* Score Bar Sidebar */}
                <aside className="score-sidebar">
                    <ScoreBar score={totalScore} />
                    {isLoading ? (
                        <div className="sidebar-loading">
                            <div className="spinner-small"></div>
                            <span className="loading-text">Evaluation ongoing</span>
                        </div>
                    ) : (
                        <div className="sidebar-complete">
                            <div className="checkmark">✓</div>
                        </div>
                    )}
                </aside>
            </div>

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
