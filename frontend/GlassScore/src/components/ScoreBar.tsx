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
    // Red: #FF6B6B (hsl(0, 100%, 71%))
    // Green: #6BCB77 (hsl(128, 48%, 61%))
    const getColor = (score: number) => {
        if (score <= 0) return 'hsl(0, 100%, 71%)'; // Red
        if (score >= 100) return 'hsl(128, 48%, 61%)'; // Green
        
        // Interpolate between red (0°) and green (128°)
        const hue = (score / 100) * 128;
        // Interpolate saturation and lightness if needed, but keeping it simple with fixed S/L for now might look weird.
        // Let's just interpolate Hue for simplicity as before, but adjust S/L to be consistent or average.
        // Previous was 70%, 45%. New are (100%, 71%) and (48%, 61%).
        // Let's use a middle ground or just the Green's S/L for the gradient to avoid muddy colors?
        // Or better, just interpolate Hue and keep S/L fixed at something that looks good for both.
        // Let's try S=80%, L=65%.
        return `hsl(${hue}, 80%, 65%)`;
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
