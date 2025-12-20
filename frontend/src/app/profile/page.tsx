import { Suspense } from 'react';
import ProfileContent from './ProfileContent';

export const dynamic = 'force-dynamic';

function LoadingProfile() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <Suspense fallback={<LoadingProfile />}>
      <ProfileContent />
    </Suspense>
  );
}
