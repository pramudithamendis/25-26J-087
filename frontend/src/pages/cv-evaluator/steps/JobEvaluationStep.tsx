interface JobEvaluationStepProps {
    onNext?: () => void;
}

export const JobEvaluationStep = ({ onNext }: JobEvaluationStepProps) => {
    return (
        <div>
            <h1>JobEvaluationStep</h1>
        </div>
    );
};