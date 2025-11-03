"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  tomorrow,
  tomorrow as tomorrowNight,
} from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTheme } from "next-themes";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({
  content,
  className = "",
}: MarkdownRendererProps) {
  const { theme } = useTheme();

  const CodeBlock = ({ node, inline, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || "");
    const language = match ? match[1] : "";

    // Extract text content properly from children
    const getTextContent = (child: any): string => {
      if (typeof child === 'string') return child;
      if (Array.isArray(child)) return child.map(getTextContent).join('');
      if (child?.props?.children) return getTextContent(child.props.children);
      return String(child || '');
    };

    const codeContent = getTextContent(children);

    if (!inline && language) {
      return (
        <SyntaxHighlighter
          style={theme === "dark" ? tomorrowNight : tomorrow}
          language={language}
          PreTag="div"
          className="rounded-lg !mt-4 !mb-4"
          {...props}
        >
          {codeContent.replace(/\n$/, "")}
        </SyntaxHighlighter>
      );
    }

    return (
      <code
        className="bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-1 py-0.5 rounded text-sm font-mono"
        {...props}
      >
        {codeContent}
      </code>
    );
  };

  const components = {
    h1: ({ children }: any) => (
      <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-8 mb-6 pb-3 border-b-2 border-blue-500 dark:border-blue-400">
        {children}
      </h1>
    ),
    h2: ({ children }: any) => (
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mt-8 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
        {children}
      </h2>
    ),
    h3: ({ children }: any) => (
      <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mt-5 mb-2">
        {children}
      </h3>
    ),
    h4: ({ children }: any) => (
      <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mt-4 mb-2">
        {children}
      </h4>
    ),
    h5: ({ children }: any) => (
      <h5 className="text-base font-medium text-gray-900 dark:text-gray-100 mt-3 mb-2">
        {children}
      </h5>
    ),
    h6: ({ children }: any) => (
      <h6 className="text-sm font-medium text-gray-900 dark:text-gray-100 mt-3 mb-2">
        {children}
      </h6>
    ),
    p: ({ children }: any) => {
      // Check if this is a metadata line (e.g., **Type:** feature)
      const childText = children?.toString() || '';
      const isMetadata = childText.match(/^\*\*[A-Z][a-z]+:\*\*/);
      
      return (
        <p className={`leading-7 mb-4 ${
          isMetadata 
            ? 'text-gray-600 dark:text-gray-400 text-sm font-medium' 
            : 'text-gray-700 dark:text-gray-300'
        }`}>
          {children}
        </p>
      );
    },
    ul: ({ children }: any) => (
      <ul className="list-disc list-outside ml-6 text-gray-700 dark:text-gray-300 mb-4 space-y-2">
        {children}
      </ul>
    ),
    ol: ({ children }: any) => (
      <ol className="list-decimal list-outside ml-6 text-gray-700 dark:text-gray-300 mb-4 space-y-2">
        {children}
      </ol>
    ),
    li: ({ children }: any) => (
      <li className="text-gray-700 dark:text-gray-300 leading-relaxed pl-2">{children}</li>
    ),
    blockquote: ({ children }: any) => (
      <blockquote className="border-l-4 border-blue-500 pl-4 my-4 italic text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 py-2 rounded-r">
        {children}
      </blockquote>
    ),
    a: ({ href, children }: any) => (
      <a
        href={href}
        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline"
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    ),
    table: ({ children }: any) => (
      <div className="overflow-x-auto my-6">
        <table className="min-w-full border border-gray-200 dark:border-gray-700 rounded-lg">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }: any) => (
      <thead className="bg-gray-50 dark:bg-gray-800">{children}</thead>
    ),
    tbody: ({ children }: any) => (
      <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
        {children}
      </tbody>
    ),
    tr: ({ children }: any) => (
      <tr className="hover:bg-gray-50 dark:hover:bg-gray-800">{children}</tr>
    ),
    th: ({ children }: any) => (
      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
        {children}
      </th>
    ),
    td: ({ children }: any) => (
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
        {children}
      </td>
    ),
    code: CodeBlock,
    pre: ({ children }: any) => (
      <pre className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 overflow-x-auto">
        {children}
      </pre>
    ),
    hr: () => <hr className="my-8 border-gray-200 dark:border-gray-700" />,
    strong: ({ children }: any) => (
      <strong className="font-semibold text-gray-900 dark:text-gray-100">
        {children}
      </strong>
    ),
    em: ({ children }: any) => (
      <em className="italic text-gray-700 dark:text-gray-300">{children}</em>
    ),
  };

  return (
    <div className={`prose prose-lg max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight, rehypeRaw]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
