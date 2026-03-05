import { CheckIcon, PencilIcon, PlusIcon, TrashIcon, XIcon } from "lucide-react";
import { useState, useEffect } from "react";
import type { CVParsed, CVSubmitResponse, Basics } from "../../../types/cv.types";
import { updateCV } from "../../../services/cv.service";

interface InfoValidationStepProps {
    cvData?: CVSubmitResponse | null;
    onNext?: () => void;
    onComplete?: (updatedCV: CVParsed) => void;
}

// Editable Field Component
const EditableField = ({
    label,
    value,
    onChange,
    type = "text",
    multiline = false
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    type?: string;
    multiline?: boolean;
}) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(value);

    const handleSave = () => {
        onChange(editValue);
        setIsEditing(false);
    };

    const handleCancel = () => {
        setEditValue(value);
        setIsEditing(false);
    };

    return (
        <div className="mb-4">
            <div className="flex items-center justify-between mb-1">
                <label className="text-sm font-medium text-gray-700">{label}</label>
                {!isEditing && (
                    <button
                        onClick={() => setIsEditing(true)}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        <PencilIcon className="h-4 w-4" />
                    </button>
                )}
            </div>

            {isEditing ? (
                <div className="space-y-2">
                    {multiline ? (
                        <textarea
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            rows={4}
                        />
                    ) : (
                        <input
                            type={type}
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    )}
                    <div className="flex space-x-2">
                        <button
                            onClick={handleSave}
                            className="px-3 py-1 bg-green-500 text-white rounded-md hover:bg-green-600 flex items-center"
                        >
                            <CheckIcon className="h-4 w-4 mr-1" />
                            Save
                        </button>
                        <button
                            onClick={handleCancel}
                            className="px-3 py-1 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 flex items-center"
                        >
                            <XIcon className="h-4 w-4 mr-1" />
                            Cancel
                        </button>
                    </div>
                </div>
            ) : (
                <p className="text-gray-900 bg-gray-50 p-2 rounded-md">
                    {value || 'Not provided'}
                </p>
            )}
        </div>
    );
};

// Editable List Component
const EditableList = ({
    items,
    onChange,
    label
}: {
    items: string[];
    onChange: (items: string[]) => void;
    label: string;
}) => {
    const [newItem, setNewItem] = useState('');

    const addItem = () => {
        if (newItem.trim()) {
            onChange([...items, newItem.trim()]);
            setNewItem('');
        }
    };

    const removeItem = (index: number) => {
        onChange(items.filter((_, i) => i !== index));
    };

    const updateItem = (index: number, value: string) => {
        const updatedItems = [...items];
        updatedItems[index] = value;
        onChange(updatedItems);
    };

    return (
        <div className="mb-4">
            <label className="text-sm font-medium text-gray-700 mb-2 block">{label}</label>
            <div className="space-y-2">
                {items.map((item, index) => (
                    <div key={index} className="flex items-center space-x-2">
                        <input
                            type="text"
                            value={item}
                            onChange={(e) => updateItem(index, e.target.value)}
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button
                            onClick={() => removeItem(index)}
                            className="p-2 text-red-500 hover:bg-red-50 rounded-md"
                        >
                            <TrashIcon className="h-4 w-4" />
                        </button>
                    </div>
                ))}
                <div className="flex items-center space-x-2">
                    <input
                        type="text"
                        value={newItem}
                        onChange={(e) => setNewItem(e.target.value)}
                        placeholder={`Add new ${label.toLowerCase()}`}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                        onClick={addItem}
                        className="px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 flex items-center"
                    >
                        <PlusIcon className="h-4 w-4 mr-1" />
                        Add
                    </button>
                </div>
            </div>
        </div>
    );
};

// Section Container
const SectionContainer = ({
    title,
    children,
    defaultOpen = false
}: {
    title: string;
    children: React.ReactNode;
    defaultOpen?: boolean;
}) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    return (
        <div className="border border-gray-200 rounded-lg mb-4">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-4 py-3 bg-gray-50 rounded-t-lg flex items-center justify-between hover:bg-gray-100"
            >
                <h3 className="text-lg font-medium text-gray-900">{title}</h3>
                <svg
                    className={`w-5 h-5 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>
            {isOpen && <div className="p-4">{children}</div>}
        </div>
    );
};

export const InfoValidationStep = ({ cvData, onNext, onComplete }: InfoValidationStepProps) => {
    const [editedData, setEditedData] = useState<CVParsed | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState(false);
    const [saveError, setSaveError] = useState('');

    useEffect(() => {
        if (cvData?.data) {
            setEditedData(cvData.data);
        }
    }, [cvData]);

    if (!editedData) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500">No CV data available. Please upload a CV first.</p>
            </div>
        );
    }

    // Safe accessors for basics fields
    const basics = editedData.basics || {} as Basics;

    const updateBasics = (field: keyof Basics, value: string) => {
        setEditedData(prev => ({
            ...prev!,
            basics: { ...prev!.basics, [field]: value }
        }));
    };

    const handleSave = async () => {
        if (!editedData) return;

        setIsSaving(true);
        setSaveError('');
        try {
            const updatedCV = await updateCV(editedData.cv_id, {
                basics: editedData.basics,
                education: editedData.education,
                work: editedData.work,
                skills: editedData.skills,
                projects: editedData.projects,
                certificates: editedData.certificates,
            });

            setSaveSuccess(true);
            setTimeout(() => setSaveSuccess(false), 3000);

            if (onComplete) {
                onComplete(updatedCV);
            }
        } catch (error: any) {
            console.error('Error saving CV data:', error);
            setSaveError(error.message || 'Failed to save changes');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Review and Confirm Your Information</h2>
                <p className="text-gray-600">
                    Please review the information extracted from your CV. You can edit any field by clicking the pencil icon.
                </p>
            </div>

            {/* Personal Information Section */}
            <SectionContainer title="Personal Information" defaultOpen={true}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <EditableField
                        label="Full Name"
                        value={basics.name || ''}
                        onChange={(value) => updateBasics('name', value)}
                    />
                    <EditableField
                        label="Email"
                        value={basics.email || ''}
                        onChange={(value) => updateBasics('email', value)}
                        type="email"
                    />
                    <EditableField
                        label="Phone"
                        value={basics.phone || ''}
                        onChange={(value) => updateBasics('phone', value)}
                    />
                    <EditableField
                        label="Address"
                        value={basics.address || ''}
                        onChange={(value) => updateBasics('address', value)}
                    />
                    <EditableField
                        label="LinkedIn"
                        value={basics.linkedin || ''}
                        onChange={(value) => updateBasics('linkedin', value)}
                    />
                    <EditableField
                        label="GitHub"
                        value={basics.github || ''}
                        onChange={(value) => updateBasics('github', value)}
                    />
                    <EditableField
                        label="Website"
                        value={basics.website || ''}
                        onChange={(value) => updateBasics('website', value)}
                    />
                </div>
                <div className="mt-4">
                    <EditableField
                        label="Professional Summary"
                        value={basics.summary || ''}
                        onChange={(value) => updateBasics('summary', value)}
                        multiline={true}
                    />
                </div>
            </SectionContainer>

            {/* Education Section */}
            <SectionContainer title="Education">
                {editedData.education.map((edu, index) => (
                    <div key={index} className="mb-6 p-4 border border-gray-100 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-3">Education #{index + 1}</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <EditableField
                                label="Institution"
                                value={edu.institution || ''}
                                onChange={(value) => {
                                    const newEducation = [...editedData.education];
                                    newEducation[index] = { ...newEducation[index], institution: value };
                                    setEditedData({ ...editedData, education: newEducation });
                                }}
                            />
                            <EditableField
                                label="Degree"
                                value={edu.studyType || ''}
                                onChange={(value) => {
                                    const newEducation = [...editedData.education];
                                    newEducation[index] = { ...newEducation[index], studyType: value };
                                    setEditedData({ ...editedData, education: newEducation });
                                }}
                            />
                            <EditableField
                                label="Field of Study"
                                value={edu.area || ''}
                                onChange={(value) => {
                                    const newEducation = [...editedData.education];
                                    newEducation[index] = { ...newEducation[index], area: value };
                                    setEditedData({ ...editedData, education: newEducation });
                                }}
                            />
                            <EditableField
                                label="GPA"
                                value={edu.gpa || ''}
                                onChange={(value) => {
                                    const newEducation = [...editedData.education];
                                    newEducation[index] = { ...newEducation[index], gpa: value };
                                    setEditedData({ ...editedData, education: newEducation });
                                }}
                            />
                            <EditableField
                                label="Start Date"
                                value={edu.startDate || ''}
                                onChange={(value) => {
                                    const newEducation = [...editedData.education];
                                    newEducation[index] = { ...newEducation[index], startDate: value };
                                    setEditedData({ ...editedData, education: newEducation });
                                }}
                            />
                            <EditableField
                                label="End Date"
                                value={edu.endDate || ''}
                                onChange={(value) => {
                                    const newEducation = [...editedData.education];
                                    newEducation[index] = { ...newEducation[index], endDate: value };
                                    setEditedData({ ...editedData, education: newEducation });
                                }}
                            />
                        </div>
                        <div className="mt-4">
                            <EditableList
                                label="Courses"
                                items={edu.courses}
                                onChange={(newCourses) => {
                                    const newEducation = [...editedData.education];
                                    newEducation[index] = { ...newEducation[index], courses: newCourses };
                                    setEditedData({ ...editedData, education: newEducation });
                                }}
                            />
                        </div>
                    </div>
                ))}
            </SectionContainer>

            {/* Work Experience Section */}
            <SectionContainer title="Work Experience">
                {editedData.work.map((work, index) => (
                    <div key={index} className="mb-6 p-4 border border-gray-100 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-3">Work Experience #{index + 1}</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <EditableField
                                label="Company"
                                value={work.name || ''}
                                onChange={(value) => {
                                    const newWork = [...editedData.work];
                                    newWork[index] = { ...newWork[index], name: value };
                                    setEditedData({ ...editedData, work: newWork });
                                }}
                            />
                            <EditableField
                                label="Position"
                                value={work.position || ''}
                                onChange={(value) => {
                                    const newWork = [...editedData.work];
                                    newWork[index] = { ...newWork[index], position: value };
                                    setEditedData({ ...editedData, work: newWork });
                                }}
                            />
                            <EditableField
                                label="Start Date"
                                value={work.startDate || ''}
                                onChange={(value) => {
                                    const newWork = [...editedData.work];
                                    newWork[index] = { ...newWork[index], startDate: value };
                                    setEditedData({ ...editedData, work: newWork });
                                }}
                            />
                            <EditableField
                                label="End Date"
                                value={work.endDate || ''}
                                onChange={(value) => {
                                    const newWork = [...editedData.work];
                                    newWork[index] = { ...newWork[index], endDate: value };
                                    setEditedData({ ...editedData, work: newWork });
                                }}
                            />
                        </div>
                        <div className="mt-4">
                            <EditableList
                                label="Highlights"
                                items={work.highlights}
                                onChange={(newHighlights) => {
                                    const newWork = [...editedData.work];
                                    newWork[index] = { ...newWork[index], highlights: newHighlights };
                                    setEditedData({ ...editedData, work: newWork });
                                }}
                            />
                        </div>
                    </div>
                ))}
            </SectionContainer>

            {/* Skills Section */}
            <SectionContainer title="Skills">
                {editedData.skills.map((skill, index) => (
                    <div key={index} className="mb-6 p-4 border border-gray-100 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-3">{skill.name || 'Unnamed Skill'}</h4>
                        <EditableList
                            label={`${skill.name || 'Skill'} Keywords`}
                            items={skill.keywords}
                            onChange={(newKeywords) => {
                                const newSkills = [...editedData.skills];
                                newSkills[index] = { ...newSkills[index], keywords: newKeywords };
                                setEditedData({ ...editedData, skills: newSkills });
                            }}
                        />
                    </div>
                ))}
            </SectionContainer>

            {/* Projects Section */}
            <SectionContainer title="Projects">
                {editedData.projects.map((project, index) => (
                    <div key={index} className="mb-6 p-4 border border-gray-100 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-3">{project.name || 'Unnamed Project'}</h4>
                        <div className="space-y-4">
                            <EditableField
                                label="Description"
                                value={project.description || ''}
                                onChange={(value) => {
                                    const newProjects = [...editedData.projects];
                                    newProjects[index] = { ...newProjects[index], description: value };
                                    setEditedData({ ...editedData, projects: newProjects });
                                }}
                                multiline={true}
                            />
                            <EditableField
                                label="URL"
                                value={project.url || ''}
                                onChange={(value) => {
                                    const newProjects = [...editedData.projects];
                                    newProjects[index] = { ...newProjects[index], url: value };
                                    setEditedData({ ...editedData, projects: newProjects });
                                }}
                            />
                        </div>
                    </div>
                ))}
            </SectionContainer>

            {/* Certificates Section */}
            <SectionContainer title="Certificates">
                {editedData.certificates.map((cert, index) => (
                    <div key={index} className="mb-6 p-4 border border-gray-100 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-3">Certificate #{index + 1}</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <EditableField
                                label="Certificate Name"
                                value={cert.name || ''}
                                onChange={(value) => {
                                    const newCerts = [...editedData.certificates];
                                    newCerts[index] = { ...newCerts[index], name: value };
                                    setEditedData({ ...editedData, certificates: newCerts });
                                }}
                            />
                            <EditableField
                                label="Issuer"
                                value={cert.issuer || ''}
                                onChange={(value) => {
                                    const newCerts = [...editedData.certificates];
                                    newCerts[index] = { ...newCerts[index], issuer: value };
                                    setEditedData({ ...editedData, certificates: newCerts });
                                }}
                            />
                            <EditableField
                                label="Date"
                                value={cert.date || ''}
                                onChange={(value) => {
                                    const newCerts = [...editedData.certificates];
                                    newCerts[index] = { ...newCerts[index], date: value };
                                    setEditedData({ ...editedData, certificates: newCerts });
                                }}
                            />
                        </div>
                    </div>
                ))}
            </SectionContainer>

            {/* Action Buttons */}
            <div className="mt-8 flex items-center justify-between">
                <div>
                    {saveSuccess && (
                        <span className="text-green-600 flex items-center">
                            <CheckIcon className="h-5 w-5 mr-1" />
                            Changes saved successfully!
                        </span>
                    )}
                    {saveError && (
                        <span className="text-red-600 text-sm">{saveError}</span>
                    )}
                </div>
                <div className="flex space-x-4">
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 flex items-center"
                    >
                        {isSaving ? (
                            <>
                                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Saving...
                            </>
                        ) : (
                            'Save Changes'
                        )}
                    </button>
                    <button
                        onClick={onNext}
                        className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                    >
                        Continue to Next Step
                    </button>
                </div>
            </div>
        </div>
    );
};