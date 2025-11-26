import React from 'react';
import './ScoreBar.css';

interface ScoreBarProps {
    score: number;
}

export const ScoreBar: React.FC<ScoreBarProps> = ({ score }) => {
    // Normalize score to 0-100 range (assuming scores can be negative)
    const normalizedScore = Math.max(0, Math.min(100, score));
    
    return (
        <div className="score-bar-vertical">
            <div className="score-value-top">{score}</div>
            <div className="score-bar-track-vertical">
                <div 
                    className="score-bar-fill-vertical" 
                    style={{ height: `${normalizedScore}%` }}
                />
            </div>
            <div className="score-label-bottom">/ 100</div>
        </div>
    );
};
