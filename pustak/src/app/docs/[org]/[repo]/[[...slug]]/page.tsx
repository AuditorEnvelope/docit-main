import RepoPage from "@/app/repo/[...slug]/page";
import { mapDocsRouteToRepoSlug } from "@/lib/docsPathMapper";

interface DocsRouteParams {
  org: string;
  repo: string;
  slug?: string[];
}

export default async function DocsRouter({
  params,
}: {
  params: Promise<DocsRouteParams>;
}) {
  const resolvedParams = await params;
  const { org, repo, slug } = resolvedParams;

  const { repoSlug } = mapDocsRouteToRepoSlug({ org, repo, slug });

  return <RepoPage params={Promise.resolve({ slug: repoSlug })} />;
}
