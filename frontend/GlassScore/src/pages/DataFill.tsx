import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { UserProfile, LoanApplication, TextContent } from '../types';
import { apiService } from '../utils/api';
import DotGrid from '../components/DotGrid';
import './DataFill.css';

interface ProfileData {
    userProfile: UserProfile;
    loanApplication: LoanApplication;
}

const HARDCODED_PROFILES: { [key: string]: ProfileData } = {
    'Datuk Allan Goh Hwan Hua': { 
        userProfile: { name: 'Datuk Allan Goh Hwan Hua', age: 45, gender: 'Male' },
        loanApplication: {
            person_age: 45,
            person_income: 120000,
            person_home_ownership: 'MORTGAGE',
            person_emp_length: 20,
            loan_intent: 'HOMEIMPROVEMENT',
            loan_grade: 'A',
            loan_amnt: 50000,
            loan_int_rate: 5.5,
            cb_person_default_on_file: 'N',
            cb_person_cred_hist_length: 20
        }
    },
    'Datuk Karim Abdullah': { 
        userProfile: { name: 'Datuk Karim Abdullah', age: 52, gender: 'Male' },
        loanApplication: {
            person_age: 52,
            person_income: 150000,
            person_home_ownership: 'OWN',
            person_emp_length: 25,
            loan_intent: 'VENTURE',
            loan_grade: 'A',
            loan_amnt: 75000,
            loan_int_rate: 4.5,
            cb_person_default_on_file: 'N',
            cb_person_cred_hist_length: 25
        }
    },
    'Sarah Tan': { 
        userProfile: { name: 'Sarah Tan', age: 28, gender: 'Female' },
        loanApplication: {
            person_age: 28,
            person_income: 90000,
            person_home_ownership: 'OWN',
            person_emp_length: 6,
            loan_intent: 'EDUCATION',
            loan_grade: 'B',
            loan_amnt: 35000,
            loan_int_rate: 6.5,
            cb_person_default_on_file: 'N',
            cb_person_cred_hist_length: 8
        }
    },
};

export const DataFill: React.FC = () => {
    const navigate = useNavigate();
    const [profile, setProfile] = useState<UserProfile>({
        name: '',
        age: 0,
        gender: ''
    });
    const [loanApp, setLoanApp] = useState<LoanApplication>({
        person_age: 0,
        person_income: 0,
        person_home_ownership: 'RENT',
        person_emp_length: 0,
        loan_intent: 'PERSONAL',
        loan_grade: 'B',
        loan_amnt: 0,
        loan_int_rate: 0,
        cb_person_default_on_file: 'N',
        cb_person_cred_hist_length: 0
    });
    const [textContentList, setTextContentList] = useState<TextContent[]>([]);
    const [newText, setNewText] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleProfileSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const selected = HARDCODED_PROFILES[e.target.value];
        if (selected) {
            setProfile(selected.userProfile);
            setLoanApp(selected.loanApplication);
        } else {
            // Reset to manual entry
            setProfile({
                name: '',
                age: 0,
                gender: ''
            });
            setLoanApp({
                person_age: 0,
                person_income: 0,
                person_home_ownership: 'RENT',
                person_emp_length: 0,
                loan_intent: 'PERSONAL',
                loan_grade: 'B',
                loan_amnt: 0,
                loan_int_rate: 0,
                cb_person_default_on_file: 'N',
                cb_person_cred_hist_length: 0
            });
        }
    };

    const handleProfileChange = (field: keyof UserProfile, value: string | number) => {
        setProfile(prev => ({ ...prev, [field]: value }));
    };

    const handleLoanChange = (field: keyof LoanApplication, value: string | number) => {
        setLoanApp(prev => ({ ...prev, [field]: value }));
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
        if (e.target.files && e.target.files.length > 0) {
            const files = Array.from(e.target.files);
            const newContents: TextContent[] = [];
            
            for (const file of files) {
                const text = await file.text();
                newContents.push({
                    text: text,
                    key: file.name,
                    source: 'File Upload'
                });
            }
            
            setTextContentList([...textContentList, ...newContents]);
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
            
            // 2. Update Profile (with loan application)
            await apiService.updateProfile(session.session_id, profile, loanApp);

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

    const isProfileValid = profile.name && profile.age > 0 && profile.gender && 
                           loanApp.person_income > 0 && loanApp.loan_amnt > 0;

    return (
        <div className="datafill-container">
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
            <div className="datafill-card">
                <div className="datafill-header">
                    <h2>Applicant Data</h2>
                    <p>Enter details and upload documents for evaluation</p>
                </div>

                <div className="datafill-content">
                    {/* Profile Section */}
                    <section className="datafill-section">
                        <h3>Applicant Profile</h3>
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
                                    value={loanApp.person_income || ''}
                                    onChange={(e) => handleLoanChange('person_income', parseFloat(e.target.value) || 0)}
                                    placeholder="Enter income"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Employment Length (years) *</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={loanApp.person_emp_length || ''}
                                    onChange={(e) => handleLoanChange('person_emp_length', parseFloat(e.target.value) || 0)}
                                    placeholder="Enter employment length"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Home Ownership *</label>
                                <select
                                    value={loanApp.person_home_ownership}
                                    onChange={(e) => handleLoanChange('person_home_ownership', e.target.value)}
                                >
                                    <option value="RENT">Rent</option>
                                    <option value="OWN">Own</option>
                                    <option value="MORTGAGE">Mortgage</option>
                                    <option value="OTHER">Other</option>
                                </select>
                            </div>

                            <div className="profile-input-group">
                                <label>Loan Amount *</label>
                                <input
                                    type="number"
                                    value={loanApp.loan_amnt || ''}
                                    onChange={(e) => handleLoanChange('loan_amnt', parseFloat(e.target.value) || 0)}
                                    placeholder="Enter loan amount"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Loan Interest Rate (%) *</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={loanApp.loan_int_rate || ''}
                                    onChange={(e) => handleLoanChange('loan_int_rate', parseFloat(e.target.value) || 0)}
                                    placeholder="Enter interest rate"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Loan Intent *</label>
                                <select
                                    value={loanApp.loan_intent}
                                    onChange={(e) => handleLoanChange('loan_intent', e.target.value)}
                                >
                                    <option value="PERSONAL">Personal</option>
                                    <option value="EDUCATION">Education</option>
                                    <option value="MEDICAL">Medical</option>
                                    <option value="VENTURE">Venture</option>
                                    <option value="DEBTCONSOLIDATION">Debt Consolidation</option>
                                    <option value="HOMEIMPROVEMENT">Home Improvement</option>
                                </select>
                            </div>

                            <div className="profile-input-group">
                                <label>Loan Grade *</label>
                                <select
                                    value={loanApp.loan_grade}
                                    onChange={(e) => handleLoanChange('loan_grade', e.target.value)}
                                >
                                    <option value="A">A</option>
                                    <option value="B">B</option>
                                    <option value="C">C</option>
                                    <option value="D">D</option>
                                    <option value="E">E</option>
                                    <option value="F">F</option>
                                    <option value="G">G</option>
                                </select>
                            </div>

                            <div className="profile-input-group">
                                <label>Credit History Length (years) *</label>
                                <input
                                    type="number"
                                    value={loanApp.cb_person_cred_hist_length || ''}
                                    onChange={(e) => handleLoanChange('cb_person_cred_hist_length', parseInt(e.target.value) || 0)}
                                    placeholder="Enter credit history length"
                                />
                            </div>

                            <div className="profile-input-group">
                                <label>Default on File *</label>
                                <select
                                    value={loanApp.cb_person_default_on_file}
                                    onChange={(e) => handleLoanChange('cb_person_default_on_file', e.target.value)}
                                >
                                    <option value="N">No</option>
                                    <option value="Y">Yes</option>
                                </select>
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
                                <span>📁 Upload File(s) (.txt, .json, .csv)</span>
                                <input type="file" accept=".txt,.json,.csv" multiple onChange={handleFileUpload} style={{ display: 'none' }} />
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
