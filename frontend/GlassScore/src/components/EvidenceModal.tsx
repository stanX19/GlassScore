import React, { useState, useEffect, useRef } from 'react';
import type { EvaluationEvidence, AppSession } from '../types';
import { COLORS } from '../utils/color';
import './EvidenceModal.css';

interface EvidenceModalProps {
    evidence: EvaluationEvidence | null;
    isOpen: boolean;
    onClose: () => void;
    onInvalidate: (evidenceId: number, reason: string) => void;
    onUndo: (evidenceId: number) => void;
    username: string;
    session: AppSession | null;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({ 
    evidence, 
    isOpen, 
    onClose, 
    onInvalidate,
    onUndo,
    username,
    session
}) => {
    const [invalidateReason, setInvalidateReason] = useState('');
    const [showTextOverlay, setShowTextOverlay] = useState(false);
    const [textContentToShow, setTextContentToShow] = useState('');
    const [citationToHighlight, setCitationToHighlight] = useState('');
    const textContentRef = useRef<HTMLDivElement>(null);

    // Effect to highlight and scroll to citation when overlay opens
    useEffect(() => {
        if (showTextOverlay && textContentRef.current && citationToHighlight) {
            // Small delay to ensure DOM is ready
            setTimeout(() => {
                const highlightElement = textContentRef.current?.querySelector('.citation-highlight');
                if (highlightElement) {
                    highlightElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);
        }
    }, [showTextOverlay, citationToHighlight]);

    // Early return AFTER all hooks
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

    const handleTextOverlayClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            setShowTextOverlay(false);
            setCitationToHighlight('');
        }
    };

    const isUrl = (str: string) => {
        try {
            new URL(str);
            return true;
        } catch {
            return false;
        }
    };

    const handleSourceClick = () => {
        if (isUrl(evidence.source)) {
            // Open URL in new tab
            window.open(evidence.source, '_blank', 'noopener,noreferrer');
        } else {
            // Check if source matches a text content key
            const textContent = session?.text_content_dict?.[evidence.source];
            if (textContent) {
                setTextContentToShow(textContent.text);
                setCitationToHighlight(evidence.citation);
                setShowTextOverlay(true);
            }
        }
    };

    // Helper function to render text with citation highlighted
    const renderHighlightedText = (text: string, citation: string) => {
        if (!citation || !text) {
            return <div>{text}</div>;
        }

        // Find citation in text (case-insensitive)
        const lowerText = text.toLowerCase();
        const lowerCitation = citation.toLowerCase().trim();
        const index = lowerText.indexOf(lowerCitation);

        if (index === -1) {
            // Citation not found, just return plain text
            return <div>{text}</div>;
        }

        // Split text into parts: before, highlighted citation, after
        const before = text.slice(0, index);
        const highlighted = text.slice(index, index + citation.length);
        const after = text.slice(index + citation.length);

        return (
            <div>
                {before}
                <span className="citation-highlight" style={{
                    backgroundColor: COLORS.YELLOW,
                    padding: '2px 4px',
                    borderRadius: '3px',
                    fontWeight: 'bold'
                }}>
                    {highlighted}
                </span>
                {after}
            </div>
        );
    };

    return (
        <>
            <div className="modal-overlay" onClick={handleOverlayClick}>
                <div className="modal-content">
                    <div className="modal-header">
                        <h3>Evidence Details</h3>
                        <button className="modal-close" onClick={onClose}>×</button>
                    </div>

                    <div className="modal-body">
                        {!evidence.valid && (
                            <div className="invalid-notice" style={{ position: 'relative' }}>
                                <strong>⚠️ This evidence has been invalidated</strong>
                                <p>{evidence.invalidate_reason}</p>
                                <button 
                                    onClick={() => onUndo(evidence.id)}
                                    className="btn-undo"
                                    style={{
                                        position: 'absolute',
                                        bottom: '0.5rem',
                                        right: '0.5rem',
                                        padding: '0.5rem 1rem',
                                        backgroundColor: COLORS.RED,
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '0.375rem',
                                        cursor: 'pointer',
                                        fontWeight: '600',
                                        fontSize: '0.875rem'
                                    }}
                                >
                                    Undo
                                </button>
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
                            <p 
                                onClick={handleSourceClick}
                                style={{ 
                                    cursor: 'pointer',
                                    color: isUrl(evidence.source) ? COLORS.BLUE : COLORS.GREEN,
                                    textDecoration: 'underline',
                                    wordBreak: 'break-all'
                                }}
                                title={isUrl(evidence.source) ? 'Click to open in new tab' : 'Click to view text content'}
                            >
                                {evidence.source}
                                {!isUrl(evidence.source) && session?.text_content_dict?.[evidence.source] && ' 📄'}
                            </p>
                        </div>

                        {evidence.valid && (
                            <div className="invalidate-section">
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

            {/* Text Content Overlay with Citation Highlighting */}
            {showTextOverlay && (
                <div className="modal-overlay" onClick={handleTextOverlayClick} style={{ zIndex: 1001 }}>
                    <div className="modal-content" style={{ maxWidth: '800px' }}>
                        <div className="modal-header">
                            <h3>Source Text Content</h3>
                            <button className="modal-close" onClick={() => {
                                setShowTextOverlay(false);
                                setCitationToHighlight('');
                            }}>×</button>
                        </div>
                        <div className="modal-body">
                            <div 
                                ref={textContentRef}
                                style={{ 
                                    whiteSpace: 'pre-wrap', 
                                    padding: '1rem', 
                                    background: '#f8f9fa', 
                                    borderRadius: '8px',
                                    maxHeight: '500px',
                                    overflowY: 'auto',
                                    lineHeight: '1.6'
                                }}
                            >
                                {renderHighlightedText(textContentToShow, citationToHighlight)}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};
