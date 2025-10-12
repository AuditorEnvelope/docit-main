import { NextRequest, NextResponse } from 'next/server';
import { loadRepoDocumentation } from '@/lib/dynamicGitHubLoader';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ repoName: string }> }
) {
  try {
    const { repoName } = await params;
    
    const docs = await loadRepoDocumentation(repoName);
    
    return NextResponse.json({
      architectureVersions: docs.architectureVersions || [],
      workflowVersions: docs.workflowVersions || [],
    });
  } catch (error) {
    console.error('Failed to fetch docs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch documentation' },
      { status: 500 }
    );
  }
}
