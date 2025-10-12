import { NextResponse } from "next/server";
import { fetchAllRepositoriesFromGitHub, hasDocsFolder } from "@/lib/realGitHubAPI";

export async function GET() {
  try {
    const repositories = await fetchAllRepositoriesFromGitHub();

    // Check which repos have docs folders
    const reposWithDocsCheck = await Promise.all(
      repositories.map(async (repo) => {
        const hasDocs = await hasDocsFolder(repo.name);
        return {
          name: repo.name,
          fullName: repo.full_name,
          description: repo.description || "No description available",
          lastUpdated: repo.updated_at,
          hasLocalDocs: hasDocs,
        };
      })
    );

    // Filter to only show repos with docs
    const reposWithDocs = reposWithDocsCheck.filter(repo => repo.hasLocalDocs);

    return NextResponse.json(reposWithDocs);
  } catch (error) {
    console.error("Failed to fetch repositories:", error);
    return NextResponse.json(
      { error: "Failed to fetch repositories" },
      { status: 500 }
    );
  }
}
