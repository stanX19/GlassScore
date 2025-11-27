import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DotGrid from '../components/DotGrid';
import './Onboarding.css';

export const Onboarding: React.FC = () => {
    const [username, setUsername] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        console.log('Onboarding component mounted');
    }, []);

    const handleEnter = () => {
        if (username.trim()) {
            localStorage.setItem('glassscore_username', username);
            navigate('/data-fill');
        }
    };

    return (
        <div className="onboarding-container">
            <div style={{ width: '100%', height: '100vh', position: 'fixed', top: 0, left: 0, zIndex: -1, pointerEvents: 'none' }}>
                <DotGrid
                    dotSize={10}
                    gap={15}
                    baseColor="rgba(77, 150, 255, 0.3)"
                    activeColor="rgba(107, 203, 119, 0.3)"
                    proximity={120}
                    shockRadius={250}
                    shockStrength={5}
                    resistance={750}
                    returnDuration={1.5}
                />
            </div>
            <h1 className="onboarding-title">GlassScore</h1>
            <div className="onboarding-card">
                <label className="onboarding-label" htmlFor="username">
                    Enter your username (Operator)
                </label>
                <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="onboarding-input"
                    placeholder="e.g. Stan"
                    onKeyDown={(e) => e.key === 'Enter' && handleEnter()}
                />
                <button
                    onClick={handleEnter}
                    disabled={!username.trim()}
                    className="onboarding-button"
                >
                    Enter System
                </button>
            </div>
        </div>
    );
};
