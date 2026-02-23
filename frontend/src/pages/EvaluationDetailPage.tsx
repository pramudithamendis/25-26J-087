import { useParams } from 'react-router-dom';
import { EvaluationDetail } from '../components/evaluations/EvaluationDetail';

export const EvaluationDetailPage = () => {
  const { evaluationId } = useParams<{ evaluationId: string }>();

  if (!evaluationId) {
    return <div>Invalid evaluation ID</div>;
  }

  return <EvaluationDetail evaluationId={evaluationId} />;
};

