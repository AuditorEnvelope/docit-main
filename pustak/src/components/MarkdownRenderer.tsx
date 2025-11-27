"use client";

import type { CSSProperties } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  tomorrow,
  tomorrow as tomorrowNight,
} from "react-syntax-highlighter/dist/esm/styles/prism";

interface MarkdownRendererProps {
  content: string;
  className?: string;
  isLight?: boolean;
}

export function MarkdownRenderer({
  content,
  className = "",
  isLight = false,
}: MarkdownRendererProps) {
  const isDark = !isLight;

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
          style={isDark ? tomorrowNight : tomorrow}
          language={language}
          PreTag="div"
          className="rounded-lg !mt-4 !mb-4"
          {...props}
        >
          {codeContent.replace(/\n$/, "")}
        </SyntaxHighlighter>
      );
    }

    const inlineClass = isDark
      ? "bg-slate-800 text-slate-200"
      : "bg-slate-200 text-slate-900";

    const inlineClasses = `${inlineClass} px-1 py-0.5 rounded text-[0.85rem] font-mono`;

    return (
      <code className={inlineClasses} {...props}>
        {codeContent}
      </code>
    );
  };

  const components = {
    h1: ({ children }: any) => (
      <h1 className={`text-[1.75rem] leading-tight font-bold mt-6 first:mt-3 mb-5 pb-3 border-b-2 ${isDark ? "text-slate-100 border-blue-400" : "text-black border-blue-500"}`}>
        {children}
      </h1>
    ),
    h2: ({ children }: any) => (
      <h2 className={`text-xl font-semibold mt-6 first:mt-4 mb-4 pb-2 border-b ${isDark ? "text-slate-100 border-slate-700" : "text-black border-slate-200"}`}>
        {children}
      </h2>
    ),
    h3: ({ children }: any) => (
      <h3 className={`text-lg font-semibold mt-5 first:mt-3 mb-2 ${isDark ? "text-slate-100" : "text-black"}`}>
        {children}
      </h3>
    ),
    h4: ({ children }: any) => (
      <h4 className={`text-base font-medium mt-4 mb-2 ${isDark ? "text-slate-100" : "text-black"}`}>
        {children}
      </h4>
    ),
    h5: ({ children }: any) => (
      <h5 className={`text-base font-medium mt-4 mb-2 ${isDark ? "text-slate-100" : "text-black"}`}>
        {children}
      </h5>
    ),
    h6: ({ children }: any) => (
      <h6 className={`text-sm font-medium mt-3 mb-2 ${isDark ? "text-slate-100" : "text-black"}`}>
        {children}
      </h6>
    ),
    p: ({ children }: any) => {
      // Check if this is a metadata line (e.g., **Type:** feature)
      const childText = children?.toString() || '';
      const isMetadata = childText.match(/^\*\*[A-Z][A-Za-z\s]+:\*\*/);
      
      return (
        <p className={`leading-7 mb-4 ${
          isMetadata 
            ? isDark ? 'text-slate-200 text-[0.9rem] font-medium' : 'text-black text-[0.9rem] font-medium'
            : isDark ? 'text-slate-200' : 'text-black'
        }`}>
          {children}
        </p>
      );
    },
    ul: ({ children }: any) => (
      <ul className={`list-disc list-outside ml-6 mb-4 space-y-1.5 ${isDark ? "text-slate-200" : "text-black"}`}>
        {children}
      </ul>
    ),
    ol: ({ children }: any) => (
      <ol className={`list-decimal list-outside ml-6 mb-4 space-y-1.5 ${isDark ? "text-slate-200" : "text-black"}`}>
        {children}
      </ol>
    ),
    li: ({ children }: any) => (
      <li className={`leading-relaxed pl-1 ${isDark ? "text-slate-200" : "text-black"}`}>
        {children}
      </li>
    ),
    blockquote: ({ children }: any) => (
      <blockquote className={`border-l-4 border-blue-500 pl-4 my-4 italic py-2 rounded-r ${isDark ? "text-slate-200 bg-slate-800/60" : "text-black bg-slate-100"}`}>
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
        <table className="min-w-full border border-slate-200 dark:border-slate-700 rounded-lg">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }: any) => (
      <thead className="bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100">
        {children}
      </thead>
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
      <td className={`px-4 py-3 text-sm ${isDark ? "text-slate-200" : "text-black"}`}>
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
      <strong className={`font-semibold ${isDark ? "text-slate-100" : "text-black"}`}>
        {children}
      </strong>
    ),
    em: ({ children }: any) => (
      <em className={`italic ${isDark ? "text-slate-300" : "text-gray-900"}`}>{children}</em>
    ),
    span: ({ children }: any) => (
      <span style={{ color: isDark ? "rgb(226 232 240)" : "#000000" }}>{children}</span>
    ),
    div: ({ children, ...props }: any) => (
      <div {...props} style={{ color: isDark ? "rgb(226 232 240)" : "#000000", ...(props?.style || {}) }}>
        {children}
      </div>
    ),
    small: ({ children }: any) => (
      <small style={{ color: isDark ? "rgb(203 213 225)" : "#000000" }}>{children}</small>
    ),
  };

  const wrapperClass = [
    "max-w-none space-y-6",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const wrapperStyle: CSSProperties = {
    color: isDark ? "rgb(226 232 240)" : "#000000",
  };

  return (
    <div className={wrapperClass} style={wrapperStyle}>
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
