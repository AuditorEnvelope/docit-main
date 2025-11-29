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

export default function Page({ params }: { params: PageParams }) {
  // Server component handles the route matching
  // and passes control to the client component
  console.log("[SERVER] Route matched with params:", params);
  
  return <ClientPage />;
}
