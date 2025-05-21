import { useParams } from 'src/routes/hooks';

import { CONFIG } from 'src/global-config';
import { useGetApplicationById } from 'src/actions/applications';

import { ApplicationDetailView } from 'src/sections/applications/view';

// ----------------------------------------------------------------------

const metadata = { title: `Application details | Dashboard - ${CONFIG.appName}` };

export default function ApplicationDetailPage() {
  const { id = '' } = useParams();

  const { application, applicationLoading, applicationError } = useGetApplicationById(id);

  return (
    <>
      <title>{metadata.title}</title>

      <ApplicationDetailView 
        application={application} 
        loading={applicationLoading} 
        error={applicationError} 
      />
    </>
  );
}