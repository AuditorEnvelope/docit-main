"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
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

interface HeadingItem {
	id: string;
	level: number;
	text: string;
}

interface MarkdownRendererProps {
	content: string;
	className?: string;
	isLight?: boolean;
	onHeadingsChange?: (headings: HeadingItem[]) => void;
}

export function MarkdownRenderer({
	content,
	className = "",
	isLight = false,
	onHeadingsChange,
}: MarkdownRendererProps) {
	const { theme } = useTheme();
	const isDark = !isLight;
	const headingStore = useRef<HeadingItem[]>([]);
	const slugCountsRef = useRef<Record<string, number>>({});

	headingStore.current = [];
	slugCountsRef.current = {};

	const extractText = (child: any): string => {
		if (typeof child === "string") return child;
		if (Array.isArray(child)) return child.map(extractText).join("");
		if (child?.props?.children) return extractText(child.props.children);
		return String(child ?? "");
	};

	const slugify = (value: string) =>
		value
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9\s-]/g, "")
			.replace(/\s+/g, "-")
			.replace(/-+/g, "-");

	const registerHeading = (level: number, rawText: string) => {
		const baseSlug =
			slugify(rawText) || `section-${headingStore.current.length + 1}`;
		const count = slugCountsRef.current[baseSlug] ?? 0;
		const slug = count > 0 ? `${baseSlug}-${count}` : baseSlug;
		slugCountsRef.current[baseSlug] = count + 1;

		const headingEntry = { id: slug, level, text: rawText };
		headingStore.current.push(headingEntry);
		return slug;
	};

	const CodeBlock = ({ node, inline, className, children, ...props }: any) => {
		const [copied, setCopied] = useState(false);
		const match = /language-(\w+)/.exec(className || "");
		const language = match ? match[1] : "";

		if (!inline && language) {
			return (
				<SyntaxHighlighter
					style={theme === "dark" ? tomorrowNight : tomorrow}
					language={language}
					PreTag="div"
					className="rounded-lg !mt-4 !mb-4"
					{...props}
				>
					{String(children).replace(/\n$/, "")}
				</SyntaxHighlighter>
			);
		}

		const inlineClass = isDark
			? "bg-slate-800/80 text-slate-100"
			: "bg-slate-100 text-slate-900";

		const inlineClasses = `${inlineClass} px-1 py-0.5 rounded text-[0.85rem] font-mono`;

		return (
			<code
				className="bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-1 py-0.5 rounded text-sm font-mono"
				{...props}
			>
				{children}
			</code>
		);
	};

	const components = {
		h1: ({ children }: any) => {
			const text = extractText(children);
			const slug = registerHeading(1, text);
			return (
				<h1
					id={slug}
					className={`scroll-mt-28 text-[2rem] leading-tight font-semibold tracking-tight mt-6 first:mt-3 mb-6 pb-3 border-b-2 ${
						isDark
							? "text-slate-100 border-indigo-400/80"
							: "text-slate-900 border-indigo-500/80"
					}`}
				>
					{children}
				</h1>
			);
		},
		h2: ({ children }: any) => {
			const text = extractText(children);
			const slug = registerHeading(2, text);
			return (
				<h2
					id={slug}
					className={`scroll-mt-28 text-xl font-semibold mt-6 first:mt-4 mb-4 pb-2 border-b ${
						isDark
							? "text-slate-100 border-slate-700/80"
							: "text-slate-900 border-slate-200"
					}`}
				>
					{children}
				</h2>
			);
		},
		h3: ({ children }: any) => {
			const text = extractText(children);
			const slug = registerHeading(3, text);
			return (
				<h3
					id={slug}
					className={`scroll-mt-28 text-lg font-semibold mt-5 first:mt-3 mb-2 ${
						isDark ? "text-slate-100" : "text-slate-900"
					}`}
				>
					{children}
				</h3>
			);
		},
		h4: ({ children }: any) => {
			const text = extractText(children);
			const slug = registerHeading(4, text);
			return (
				<h4
					id={slug}
					className={`scroll-mt-28 text-base font-medium mt-4 mb-2 ${
						isDark ? "text-slate-100" : "text-black"
					}`}
				>
					{children}
				</h4>
			);
		},
		h5: ({ children }: any) => {
			const text = extractText(children);
			const slug = registerHeading(5, text);
			return (
				<h5
					id={slug}
					className={`scroll-mt-28 text-base font-medium mt-4 mb-2 ${
						isDark ? "text-slate-100" : "text-black"
					}`}
				>
					{children}
				</h5>
			);
		},
		h6: ({ children }: any) => {
			const text = extractText(children);
			const slug = registerHeading(6, text);
			return (
				<h6
					id={slug}
					className={`scroll-mt-28 text-sm font-medium mt-3 mb-2 ${
						isDark ? "text-slate-100" : "text-black"
					}`}
				>
					{children}
				</h6>
			);
		},
		p: ({ children }: any) => {
			// Check if this is a metadata line (e.g., **Type:** feature)
			const childText = children?.toString() || "";
			const isMetadata = childText.match(/^\*\*[A-Z][A-Za-z\s]+:\*\*/);

			return (
				<p
					className={`leading-7 mb-5 ${
						isMetadata
							? isDark
								? "text-slate-200 text-[0.9rem] font-semibold tracking-wide"
								: "text-slate-800 text-[0.9rem] font-semibold tracking-wide"
							: isDark
								? "text-slate-300"
								: "text-slate-700"
					}`}
				>
					{children}
				</p>
			);
		},
		ul: ({ children }: any) => (
			<ul
				className={`list-disc list-outside ml-6 mb-5 space-y-2 ${isDark ? "text-slate-200" : "text-slate-700"}`}
			>
				{children}
			</ul>
		),
		ol: ({ children }: any) => (
			<ol
				className={`list-decimal list-outside ml-6 mb-5 space-y-2 ${isDark ? "text-slate-200" : "text-slate-700"}`}
			>
				{children}
			</ol>
		),
		li: ({ children }: any) => (
			<li
				className={`leading-relaxed pl-1 ${isDark ? "text-slate-200" : "text-slate-700"}`}
			>
				{children}
			</li>
		),
		blockquote: ({ children }: any) => (
			<blockquote
				className={`my-6 overflow-hidden rounded-2xl border px-5 py-4 text-sm ${
					isDark
						? "border-indigo-500/40 bg-indigo-500/5 text-slate-200"
						: "border-indigo-200 bg-indigo-50 text-slate-700"
				}`}
			>
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
			<div className="my-6 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
				<table className="min-w-full text-sm">{children}</table>
			</div>
		),
		thead: ({ children }: any) => (
			<thead className="bg-slate-100/70 text-slate-900 dark:bg-slate-900/70 dark:text-slate-100">
				{children}
			</thead>
		),
		tbody: ({ children }: any) => (
			<tbody className="divide-y divide-slate-200 dark:divide-slate-800">
				{children}
			</tbody>
		),
		tr: ({ children }: any) => (
			<tr className="hover:bg-slate-50 dark:hover:bg-slate-800/60">
				{children}
			</tr>
		),
		th: ({ children }: any) => (
			<th className="px-4 py-3 text-left text-[0.7rem] font-semibold uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
				{children}
			</th>
		),
		td: ({ children }: any) => (
			<td
				className={`px-4 py-3 text-sm ${isDark ? "text-slate-200" : "text-slate-700"}`}
			>
				{children}
			</td>
		),
		code: CodeBlock,
		pre: ({ children }: any) => (
			<pre className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 overflow-x-auto">
				{children}
			</pre>
		),
		hr: () => <hr className="my-8 border-slate-200 dark:border-slate-800" />,
		strong: ({ children }: any) => (
			<strong
				className={`font-semibold ${isDark ? "text-slate-100" : "text-black"}`}
			>
				{children}
			</strong>
		),
		em: ({ children }: any) => (
			<em className={`italic ${isDark ? "text-slate-300" : "text-gray-900"}`}>
				{children}
			</em>
		),
		span: ({ children }: any) => (
			<span style={{ color: isDark ? "rgb(226 232 240)" : "#000000" }}>
				{children}
			</span>
		),
		div: ({ children, ...props }: any) => (
			<div
				{...props}
				style={{
					color: isDark ? "rgb(226 232 240)" : "#000000",
					...(props?.style || {}),
				}}
			>
				{children}
			</div>
		),
		small: ({ children }: any) => (
			<small style={{ color: isDark ? "rgb(203 213 225)" : "#000000" }}>
				{children}
			</small>
		),
	};

	const wrapperClass = ["max-w-none space-y-6", className]
		.filter(Boolean)
		.join(" ");

	const wrapperStyle: CSSProperties = {
		color: isDark ? "rgb(226 232 240)" : "#000000",
	};

	useEffect(() => {
		if (onHeadingsChange) {
			onHeadingsChange([...headingStore.current]);
		}
	}, [content, onHeadingsChange]);

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
