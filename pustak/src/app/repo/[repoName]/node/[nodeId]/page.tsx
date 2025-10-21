import { TreeSidebar } from "@/components/TreeSidebar";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { NodeContent } from "@/components/NodeContent";

interface PageProps {
  params: {
    repoName: string;
    nodeId: string;
  };
}

async function getNodeDetails(repoName: string, nodeId: string) {
  try {
    const response = await fetch(
      `http://localhost:8000/api/repos/${encodeURIComponent(repoName)}/node/${nodeId}`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch node: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching node:", error);
    return null;
  }
}

export default async function NodePage({ params }: PageProps) {
  const { repoName, nodeId } = await params;
  const node = await getNodeDetails(repoName, nodeId);

  if (!node) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4 py-8">
          <h1 className="text-2xl font-bold text-red-600">Node not found</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Could not load documentation for this node.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex h-screen">
        {/* Sidebar */}
        <aside className="w-64 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 overflow-y-auto">
          <div className="p-4 border-b border-gray-200 dark:border-gray-800">
            <h1 className="text-lg font-semibold truncate">{repoName}</h1>
          </div>
          <TreeSidebar repoName={repoName} currentPath={node.path} />
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-8 py-6">
            {/* Breadcrumbs */}
            <Breadcrumbs node={node} repoName={repoName} />

            {/* Node content */}
            <div className="mt-6">
              <NodeContent node={node} />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
