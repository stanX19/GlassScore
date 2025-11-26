import React from 'react';
import './ScoreBar.css';

interface ScoreBarProps {
    score: number;
}

export const ScoreBar: React.FC<ScoreBarProps> = ({ score }) => {
    // Calculate percentage fill (0% at 0, 100% cap)
    // Can display negative and over 100, but bar is capped at 0-100%
    const fillPercentage = Math.max(0, Math.min(100, score));
    
    // Calculate color based on score (red at 0, green at 100)
    // Use HSL color: 0° is red, 120° is green
    const getColor = (score: number) => {
        if (score <= 0) return 'hsl(0, 70%, 50%)'; // Red
        if (score >= 100) return 'hsl(120, 70%, 40%)'; // Green
        
        // Interpolate between red (0°) and green (120°)
        const hue = (score / 100) * 120;
        return `hsl(${hue}, 70%, 45%)`;
    };
    
    const barColor = getColor(score);
    
    return (
        <div className="score-bar-vertical">
            <div className="score-bar-track-vertical">
                <div 
                    className="score-bar-fill-vertical" 
                    style={{ 
                        height: `${fillPercentage}%`,
                        backgroundColor: barColor
                    }}
                />
            </div>
            <div className="score-value-top" style={{ 
                color: '#1f2937',
                fontWeight: 'bold',
                fontSize: '2rem',
                marginTop: '1rem'
            }}>
                {score}
            </div>
        </div>
    );
};
