import { useParams } from 'react-router-dom';
import { JobDetail } from '../components/jobs/JobDetail';

export const JobDetailPage = () => {
  const { jobId } = useParams<{ jobId: string }>();

  if (!jobId) {
    return <div>Invalid job ID</div>;
  }

  return <JobDetail jobId={jobId} />;
};

