/**
 * Workspace Page - Entry Point for Testing
 * 
 * Route: /workspace/{org}/{repo}
 * Example: /workspace/midnight-testing/midnight
 */

'use client';

import { UnifiedWorkspace } from '@/components/workspace/UnifiedWorkspace';
import { use } from 'react';

interface PageProps {
  params: Promise<{
    org: string;
    repo: string;
  }>;
}

export default function WorkspacePage({ params }: PageProps) {
  const { org, repo } = use(params);

  return <UnifiedWorkspace orgId={org} repoId={repo} />;
}
