import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { UserProfile, TextContent } from '../types';
import { apiService } from '../utils/api';
import './DataFill.css';

const HARDCODED_PROFILES: { [key: string]: UserProfile } = {
    'John Doe': { name: 'John Doe', age: 30, gender: 'Male', income: 75000, loan_amount: 20000, loan_term: 12 },
    'Jane Smith': { name: 'Jane Smith', age: 28, gender: 'Female', income: 90000, loan_amount: 35000, loan_term: 24 },
    'Bob Johnson': { name: 'Bob Johnson', age: 45, gender: 'Male', income: 120000, loan_amount: 50000, loan_term: 36 },
    'Alice Williams': { name: 'Alice Williams', age: 35, gender: 'Female', income: 60000, loan_amount: 15000, loan_term: 12 },
    'Charlie Brown': { name: 'Charlie Brown', age: 50, gender: 'Male', income: 150000, loan_amount: 100000, loan_term: 60 },
};

export const DataFill: React.FC = () => {
    const navigate = useNavigate();
    const [profile, setProfile] = useState<UserProfile>({
        name: '',
        age: 0,
        gender: '',
        income: 0,
        loan_amount: 0,
        loan_term: 0
    });
    const [textContentList, setTextContentList] = useState<TextContent[]>([]);
    const [newText, setNewText] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleProfileSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const selected = HARDCODED_PROFILES[e.target.value];
        if (selected) {
            setProfile(selected);
        } else {
            // Reset to manual entry
            setProfile({
                name: '',
                age: 0,
                gender: '',
                income: 0,
                loan_amount: 0,
                loan_term: 0
            });
        }
    };

    const handleProfileChange = (field: keyof UserProfile, value: string | number) => {
        setProfile(prev => ({ ...prev, [field]: value }));
    };

    const handleAddText = () => {
        if (newText.trim()) {
            setTextContentList([...textContentList, {
                text: newText,
                key: `manual_entry_${Date.now()}.txt`,
                source: 'Manual Entry'
            }]);
            setNewText('');
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            const text = await file.text();
            setTextContentList([...textContentList, {
                text: text,
                key: file.name,
                source: 'File Upload'
            }]);
            e.target.value = ''; // Reset input
        }
    };

    const handleRemoveContent = (index: number) => {
        setTextContentList(textContentList.filter((_, i) => i !== index));
    };

    const handleStartEvaluation = async () => {
        setIsLoading(true);
        try {
            // 1. Create Session
            const session = await apiService.createSession();
            
            // 2. Update Profile
            await apiService.updateProfile(session.session_id, profile);

            // 3. Attach Content
            for (const content of textContentList) {
                await apiService.attachContent(session.session_id, content);
            }

            // 4. Start Evaluation (Trigger background tasks)
            await apiService.startEvaluation(session.session_id);

            // Navigate to Evaluation
            navigate('/evaluation', { state: { sessionId: session.session_id, profileName: profile.name } });
        } catch (error) {
            console.error('Failed to start evaluation:', error);
            alert('Failed to start evaluation. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const isProfileValid = profile.name && profile.age > 0 && profile.gender && profile.income > 0 && profile.loan_amount > 0 && profile.loan_term > 0;

    return (
        <div className="datafill-container">
            <div className="datafill-card">
                <div className="datafill-header">
                    <h2>Applicant Data</h2>
                    <p>Enter details and upload documents for evaluation</p>
                </div>

                <div className="datafill-content">
                    {/* Profile Section */}
                    <section className="datafill-section">
                        <h3>User Profile</h3>
                        <div className="profile-grid">
                            <div className="profile-input-group">
                                <label>Load Preset Profile</label>
                                <select onChange={handleProfileSelect} defaultValue="">
                                    <option value="">Manual Entry</option>
                                    {Object.keys(HARDCODED_PROFILES).map(name => (
                                        <option key={name} value={name}>{name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="profile-input-group">
                                <label>Name *</label>
                                <input
                                    type="text"
                                    value={profile.name}
                                    onChange={(e) => handleProfileChange('name', e.target.value)}
                                    placeholder="Enter name"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Age *</label>
                                <input
                                    type="number"
                                    value={profile.age || ''}
                                    onChange={(e) => handleProfileChange('age', parseInt(e.target.value) || 0)}
                                    placeholder="Enter age"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Gender *</label>
                                <select
                                    value={profile.gender}
                                    onChange={(e) => handleProfileChange('gender', e.target.value)}
                                >
                                    <option value="">Select gender</option>
                                    <option value="Male">Male</option>
                                    <option value="Female">Female</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>

                            <div className="profile-input-group">
                                <label>Annual Income *</label>
                                <input
                                    type="number"
                                    value={profile.income || ''}
                                    onChange={(e) => handleProfileChange('income', parseInt(e.target.value) || 0)}
                                    placeholder="Enter income"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Loan Amount *</label>
                                <input
                                    type="number"
                                    value={profile.loan_amount || ''}
                                    onChange={(e) => handleProfileChange('loan_amount', parseInt(e.target.value) || 0)}
                                    placeholder="Enter loan amount"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Loan Term (months) *</label>
                                <input
                                    type="number"
                                    value={profile.loan_term || ''}
                                    onChange={(e) => handleProfileChange('loan_term', parseInt(e.target.value) || 0)}
                                    placeholder="Enter loan term"
                                />
                            </div>
                        </div>
                    </section>

                    {/* Content Section */}
                    <section className="datafill-section">
                        <h3>Supporting Documents</h3>
                        
                        <textarea
                            value={newText}
                            onChange={(e) => setNewText(e.target.value)}
                            placeholder="Paste text content here..."
                            className="content-textarea"
                        />
                        
                        <div className="content-actions">
                            <label className="btn-upload">
                                <span>📁 Upload File (.txt)</span>
                                <input type="file" accept=".txt" onChange={handleFileUpload} style={{ display: 'none' }} />
                            </label>
                            <button 
                                onClick={handleAddText}
                                disabled={!newText.trim()}
                                className="btn-add"
                            >
                                Add Text
                            </button>
                        </div>

                        <div className="content-list" style={{ marginTop: '1rem' }}>
                            {textContentList.map((content, index) => (
                                <div key={index} className="content-item">
                                    <div className="content-item-info">
                                        <p className="content-item-title">{content.key}</p>
                                        <p className="content-item-meta">{content.source} • {content.text.length} chars</p>
                                    </div>
                                    <button 
                                        onClick={() => handleRemoveContent(index)}
                                        className="btn-remove"
                                    >
                                        Remove
                                    </button>
                                </div>
                            ))}
                            {textContentList.length === 0 && (
                                <p className="content-empty">No documents added yet</p>
                            )}
                        </div>
                    </section>

                    <button
                        onClick={handleStartEvaluation}
                        disabled={isLoading || !isProfileValid || textContentList.length === 0}
                        className="btn-start-evaluation"
                    >
                        {isLoading ? 'Initializing Session...' : 'Start Evaluation'}
                    </button>
                </div>
            </div>
        </div>
    );
};
