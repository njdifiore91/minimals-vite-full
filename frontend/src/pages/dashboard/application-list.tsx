import { CONFIG } from 'src/global-config';

import { ApplicationListView } from 'src/sections/applications/view';

// ----------------------------------------------------------------------

const metadata = { title: `Application list | Dashboard - ${CONFIG.appName}` };

export default function ApplicationListPage() {
  return (
    <>
      <title>{metadata.title}</title>

      <ApplicationListView />
    </>
  );
}