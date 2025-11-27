import React from 'react';
import './ScoreBar.css';

interface ScoreBarProps {
    score: number;
    orientation?: 'vertical' | 'horizontal';
}

export const ScoreBar: React.FC<ScoreBarProps> = ({ score, orientation = 'horizontal' }) => {
    // Calculate percentage fill (0% at 0, 100% cap)
    // Can display negative and over 100, but bar is capped at 0-100%
    const fillPercentage = Math.max(0, Math.min(100, score));
    
    // Clamp displayed score to 0-100 range
    const displayedScore = Math.max(0, Math.min(100, score));
    
    // Calculate color based on score with discrete thresholds
    // <50: Red, <75: Orange, >=75: Green (following palette)
    const getColor = (score: number) => {
        const clampedScore = Math.max(0, Math.min(100, score));
        if (clampedScore < 30) return 'var(--color-red)';
        if (clampedScore < 60) return 'var(--color-orange)';
        return 'var(--color-green)';
    };
    
    const getBackgroundColor = (score: number) => {
        const clampedScore = Math.max(0, Math.min(100, score));
        if (clampedScore < 30) return 'color-mix(in srgb, var(--color-red), white 80%)';
        if (clampedScore < 60) return 'color-mix(in srgb, var(--color-orange), white 80%)';
        return 'color-mix(in srgb, var(--color-green), white 80%)';
    };
    
    const barColor = getColor(score);
    const backgroundColor = getBackgroundColor(score);
    
    if (orientation === 'horizontal') {
        return (
            <div className="score-bar-horizontal-container">
                <div className="score-bar-track-horizontal" style={{ backgroundColor }}>
                    <div 
                        className="score-bar-fill-horizontal" 
                        style={{ 
                            width: `${fillPercentage}%`,
                            backgroundColor: barColor
                        }}
                    />
                </div>
                <div className="score-value-horizontal-display" style={{ color: barColor }}>
                    {displayedScore}
                </div>
            </div>
        );
    }
    
    return (
        <div className="score-bar-vertical">
            <div className="score-bar-track-vertical" style={{ backgroundColor }}>
                <div 
                    className="score-bar-fill-vertical" 
                    style={{ 
                        height: `${fillPercentage}%`,
                        backgroundColor: barColor
                    }}
                />
            </div>
            <div className="score-value-top" style={{ 
                color: barColor,
                fontWeight: 'bold',
                fontSize: '2rem',
                marginTop: '1rem'
            }}>
                {displayedScore}
            </div>
        </div>
    );
};
