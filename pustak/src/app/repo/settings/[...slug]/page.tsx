"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import DocPersonaSelector from "@/components/DocPersonaSelector";
import { ArrowLeft, Settings, Loader2 } from "lucide-react";
import Link from "next/link";

interface SettingsPageProps {
  params: Promise<{
    slug: string[];
  }>;
}

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function RepositorySettingsPage({ params }: SettingsPageProps) {
  const router = useRouter();
  const [repoName, setRepoName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [userToken, setUserToken] = useState<string>("");

  useEffect(() => {
    let isMounted = true;

    async function loadPage() {
      try {
        const resolvedParams = await params;
        const slug = resolvedParams.slug;

        // Extract repo name from slug
        const repoPath = slug.join("/");

        if (!isMounted) return;

        setRepoName(repoPath);

        // Get user token from localStorage
        const token = localStorage.getItem("pustak_access_token");
        if (token) {
          setUserToken(token);
        }

        setLoading(false);
      } catch (error) {
        console.error("Error loading settings page:", error);
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadPage();

    return () => {
      isMounted = false;
    };
  }, [params]);

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <Link
              href={`/repo/${repoName}`}
              className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Repository
            </Link>

            <div className="flex items-center gap-3">
              <Settings className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  Repository Settings
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  {repoName}
                </p>
              </div>
            </div>
          </div>

          {/* Settings Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Main Content */}
            <div className="lg:col-span-2">
              {/* Doc Persona Section */}
              <div className="mb-8">
                <DocPersonaSelector
                  repoId={repoName}
                  backendUrl={BACKEND_URL}
                  userToken={userToken}
                  onSave={(persona) => {
                    console.log(`✅ Saved doc_persona: ${persona}`);
                  }}
                />
              </div>

              {/* Additional Settings (Future) */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
                  Other Settings
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  More settings coming soon...
                </p>
              </div>
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-1">
              {/* Info Card */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
                <h4 className="font-semibold text-blue-900 dark:text-blue-300 mb-3">
                  💡 Documentation Personas
                </h4>
                <div className="space-y-3 text-sm text-blue-800 dark:text-blue-200">
                  <div>
                    <p className="font-medium">Internal</p>
                    <p className="text-xs opacity-75">
                      For staff engineers. Includes detailed architecture and implementation.
                    </p>
                  </div>
                  <div>
                    <p className="font-medium">Developer</p>
                    <p className="text-xs opacity-75">
                      For external partners. Focuses on APIs and usage examples.
                    </p>
                  </div>
                </div>
              </div>

              {/* Help Card */}
              <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-3">
                  ❓ Need Help?
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  The documentation persona determines what type of documentation is generated
                  for your repository.
                </p>
                <a
                  href="#"
                  className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium mt-3 inline-block"
                >
                  Learn more →
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
