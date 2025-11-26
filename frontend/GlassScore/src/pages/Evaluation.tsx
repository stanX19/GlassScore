import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiService } from '../utils/api';
import type { EvaluationEvidence } from '../types';
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

        const initSession = async () => {
            try {
                // First, try to fetch existing session data
                const session = await apiService.getSession(sessionId);
                if (session.evidence_list && session.evidence_list.length > 0) {
                    // Evidence already exists, just display it (don't re-stream to avoid duplicates)
                    setEvidences(session.evidence_list);
                    setIsLoading(false);
                    return; // Don't start streaming
                }
            } catch (error) {
                console.error('Failed to fetch existing session:', error);
                // Continue to streaming if fetch fails
            }

            // If no existing evidence, start streaming
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
                            setIsLoading(false);
                            break;
                        }
                        
                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\n');
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    setEvidences(prev => {
                                        // Avoid duplicates by ID
                                        if (prev.find(e => e.id === data.id)) return prev;
                                        return [...prev, data];
                                    });
                                    setIsLoading(false);
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
    }, [sessionId, navigate, username]);

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

    // Separate and sort evidences
    const validEvidences = evidences.filter(e => e.valid);
    const positiveNeutral = validEvidences.filter(e => e.score >= 0).sort((a, b) => b.score - a.score);
    const negative = validEvidences.filter(e => e.score < 0).sort((a, b) => a.score - b.score);
    const invalidated = evidences.filter(e => !e.valid);

    // Calculate column distribution (out of 4 total columns)
    const totalValid = positiveNeutral.length + negative.length;
    let positiveCols = 2;
    let negativeCols = 2;

    if (totalValid > 0) {
        const ratio = positiveNeutral.length / totalValid;
        positiveCols = Math.max(1, Math.min(3, Math.round(ratio * 4)));
        negativeCols = 4 - positiveCols;
    }

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
                        <div className="evidence-sections">
                            {/* Positive/Neutral Section */}
                            {positiveNeutral.length > 0 && (
                                <div className="evidence-section">
                                    <h2 className="section-title positive-title">
                                        Positive & Neutral Evidence ({positiveNeutral.length})
                                    </h2>
                                    <div 
                                        className="evidence-grid" 
                                        style={{ 
                                            gridTemplateColumns: `repeat(${positiveCols}, 1fr)` 
                                        }}
                                    >
                                        {positiveNeutral.map((evidence) => (
                                            <EvidenceCard 
                                                key={evidence.id} 
                                                evidence={evidence} 
                                                onClick={() => handleEvidenceClick(evidence)} 
                                            />
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Negative Section */}
                            {negative.length > 0 && (
                                <div className="evidence-section">
                                    <h2 className="section-title negative-title">
                                        Negative Evidence ({negative.length})
                                    </h2>
                                    <div 
                                        className="evidence-grid" 
                                        style={{ 
                                            gridTemplateColumns: `repeat(${negativeCols}, 1fr)` 
                                        }}
                                    >
                                        {negative.map((evidence) => (
                                            <EvidenceCard 
                                                key={evidence.id} 
                                                evidence={evidence} 
                                                onClick={() => handleEvidenceClick(evidence)} 
                                            />
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Invalidated Section */}
                            {invalidated.length > 0 && (
                                <div className="evidence-section">
                                    <h2 className="section-title invalidated-title">
                                        Invalidated Evidence ({invalidated.length})
                                    </h2>
                                    <div className="evidence-grid">
                                        {invalidated.map((evidence) => (
                                            <EvidenceCard 
                                                key={evidence.id} 
                                                evidence={evidence} 
                                                onClick={() => handleEvidenceClick(evidence)} 
                                            />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </main>

                {/* Score Bar Sidebar */}
                <aside className="score-sidebar">
                    <ScoreBar score={totalScore} />
                </aside>
            </div>

            {/* Modal */}
            <EvidenceModal 
                evidence={selectedEvidence}
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onInvalidate={handleInvalidate}
                username={username}
            />
        </div>
    );
};
