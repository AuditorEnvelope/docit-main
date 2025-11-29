// Server component wrapper for dynamic routing
// This ensures Next.js can match the route on the server
export const dynamic = "force-dynamic";
export const revalidate = 0;

// Import the client component
import ClientPage from "./client-page";

interface PageParams {
  org: string;
  repo: string;
  persona: string;
  slug?: string[];
}

// Next.js 15 requires params to be async
export default async function Page({ 
  params 
}: { 
  params: Promise<PageParams> 
}) {
  // Await the params since they're now async in Next.js 15
  const resolvedParams = await params;
  
  // Server component handles the route matching
  // and passes control to the client component
  console.log("[SERVER] Route matched with params:", resolvedParams);
  
  // Pass the params to the client component as props
  // The client component will use these instead of useParams()
  return <ClientPage initialParams={resolvedParams} />;
}
