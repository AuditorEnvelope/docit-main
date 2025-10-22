"use client";

import { use, useEffect, useState } from 'react';
import { Layout } from "@/components/Layout";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeHighlight from 'rehype-highlight';
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import 'highlight.js/styles/github-dark.css';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface RepoPageProps {
  params: Promise<{
    slug: string[];
  }>;
}

export default function RepoPage({ params }: RepoPageProps) {
  const { slug } = use(params);
  
  // Parse slug: last item is docType, rest is repo name
  // Example: ['Testing-Org-For-Pustak', 'Testing', 'summary']
  // repoName = 'Testing-Org-For-Pustak/Testing'
  // docType = 'summary'
  const docType = slug[slug.length - 1];
  const repoName = slug.slice(0, -1).join('/');
  
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDoc() {
      console.log('🚀 Starting fetch for:', repoName, docType);
      
      try {
        // Get token from localStorage directly
        const jwtToken = localStorage.getItem('pustak_access_token');
        console.log('🔑 JWT Token:', !!jwtToken);
        
        if (!jwtToken) {
          setError('Please login to view documentation');
          setLoading(false);
          return;
        }

        // Step 1: Get GitHub token from backend
        console.log('📡 Fetching GitHub token...');
        const tokenResponse = await fetch(`${BACKEND_URL}/auth/github-token`, {
          headers: {
            'Authorization': `Bearer ${jwtToken}`,
          },
        });

        if (!tokenResponse.ok) {
          throw new Error('Failed to get GitHub token');
        }

        const { token: githubToken } = await tokenResponse.json();
        console.log('✅ Got GitHub token');

        // Step 2: Fetch doc file from GitHub
        const fileMap: Record<string, string> = {
          summary: 'SUMMARY.md',
          architecture: 'ARCHITECTURE.md',
          api: 'API.md',
          changelog: 'CHANGELOG.md',
          workflow: 'WORKFLOW.md',
          overview: 'README.md',
        };

        const fileName = fileMap[docType] || 'SUMMARY.md';
        const filePath = `docs/${fileName}`;
        
        console.log('📡 Fetching:', `${repoName}/${filePath}`);

        const response = await fetch(
          `https://api.github.com/repos/${repoName}/contents/${filePath}`,
          {
            headers: {
              'Authorization': `token ${githubToken}`,
              'Accept': 'application/vnd.github.v3+json',
            },
          }
        );

        console.log('📥 GitHub response:', response.status);

        if (!response.ok) {
          throw new Error(`Failed to fetch ${fileName}: ${response.status}`);
        }

        const data = await response.json();
        const decoded = atob(data.content);
        
        console.log('✅ Got content, length:', decoded.length);
        setContent(decoded);
        setLoading(false);
      } catch (err) {
        console.error('❌ Error:', err);
        setError(`Failed to load documentation: ${err instanceof Error ? err.message : 'Unknown error'}`);
        setLoading(false);
      }
    }

    fetchDoc();
  }, [repoName, docType]);

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto p-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Error Loading Documentation
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-8">
              {error}
            </p>
            <Link
              href="/"
              className="inline-flex items-center space-x-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Home</span>
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-5xl mx-auto p-6">
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center space-x-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </Link>

          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            {docType.charAt(0).toUpperCase() + docType.slice(1)}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">{repoName}</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
          <div className="markdown-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw, rehypeHighlight]}
              components={{
                h1: ({node, ...props}) => <h1 className="text-3xl font-bold mb-4 text-gray-900 dark:text-gray-100" {...props} />,
                h2: ({node, ...props}) => <h2 className="text-2xl font-bold mb-3 mt-6 text-gray-900 dark:text-gray-100" {...props} />,
                h3: ({node, ...props}) => <h3 className="text-xl font-bold mb-2 mt-4 text-gray-900 dark:text-gray-100" {...props} />,
                p: ({node, ...props}) => <p className="mb-4 text-gray-700 dark:text-gray-300 leading-7" {...props} />,
                ul: ({node, ...props}) => <ul className="list-disc list-inside mb-4 space-y-2 text-gray-700 dark:text-gray-300" {...props} />,
                ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-4 space-y-2 text-gray-700 dark:text-gray-300" {...props} />,
                li: ({node, ...props}) => <li className="ml-4" {...props} />,
                code: ({node, inline, ...props}: any) => 
                  inline ? (
                    <code className="bg-gray-100 dark:bg-gray-900 px-1.5 py-0.5 rounded text-sm font-mono text-red-600 dark:text-red-400" {...props} />
                  ) : (
                    <code className="block bg-gray-100 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto text-sm font-mono" {...props} />
                  ),
                pre: ({node, ...props}) => <pre className="mb-4 overflow-x-auto" {...props} />,
                a: ({node, ...props}) => <a className="text-blue-600 dark:text-blue-400 hover:underline" {...props} />,
                blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-gray-300 dark:border-gray-700 pl-4 italic my-4 text-gray-600 dark:text-gray-400" {...props} />,
                table: ({node, ...props}) => <table className="min-w-full border-collapse border border-gray-300 dark:border-gray-700 my-4" {...props} />,
                th: ({node, ...props}) => <th className="border border-gray-300 dark:border-gray-700 px-4 py-2 bg-gray-100 dark:bg-gray-800 font-bold text-left" {...props} />,
                td: ({node, ...props}) => <td className="border border-gray-300 dark:border-gray-700 px-4 py-2" {...props} />,
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </Layout>
  );
}
