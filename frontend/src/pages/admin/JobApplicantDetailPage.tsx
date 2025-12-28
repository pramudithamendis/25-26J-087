import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../../components/Button';
import { JobApplicantDetail } from '../../components/admin/JobApplicantDetail';

export const JobApplicantDetailPage = () => {
  const { jobId, applicationId } = useParams<{ jobId: string; applicationId: string }>();
  const navigate = useNavigate();

  if (!jobId || !applicationId) {
    return (
      <div>
        <p className="text-red-600">Invalid job ID or application ID</p>
        <Button variant="outline" onClick={() => navigate('/dashboard/admin/jobs')} className="mt-4">
          Back to Jobs
        </Button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Button
          variant="outline"
          onClick={() => navigate(`/dashboard/admin/jobs/${jobId}/applicants`)}
        >
          ← Back to Applicants
        </Button>
      </div>
      <JobApplicantDetail applicationId={applicationId} jobId={jobId} />
    </div>
  );
};

