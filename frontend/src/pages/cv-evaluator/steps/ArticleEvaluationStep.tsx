interface ArticleEvaluationStepProps {
    onNext?: () => void;
}

export const ArticleEvaluationStep = ({ onNext }: ArticleEvaluationStepProps) => {
    return (
        <div>
            <h1>Article Evaluation Step</h1>
        </div>
    );
};