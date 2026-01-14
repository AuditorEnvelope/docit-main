"use client";

import { useState, useEffect } from "react";
import {
	Zap,
	CheckCircle,
	AlertCircle,
	Loader2,
	RefreshCw,
	ArrowUpCircle,
} from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import { isUsageLimitError, type UsageLimitError } from "@/lib/usage";

const BACKEND_URL =
	process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface GenerateDocsButtonProps {
	repoName: string;
	repoFullName: string;
	hasDocsFolder: boolean;
	docPersona?: string;
	onGenerationStart?: () => void;
	onGenerationComplete?: () => void;
	disabled?: boolean;
	disabledReason?: string;
	fullWidth?: boolean;
}

export function GenerateDocsButton({
	repoName,
	repoFullName,
	hasDocsFolder,
	docPersona: propDocPersona = "internal",
	onGenerationStart,
	onGenerationComplete,
	disabled = false,
	disabledReason,
	fullWidth = false,
}: GenerateDocsButtonProps) {
	const [isGenerating, setIsGenerating] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [success, setSuccess] = useState(false);
	const [docPersona, setDocPersona] = useState<string>(propDocPersona);
	const [isLoadingPersona, setIsLoadingPersona] = useState(false);
	const [usageLimitError, setUsageLimitError] =
		useState<UsageLimitError | null>(null);
	const { token } = useAuth();

	// Fetch the current doc_persona from the backend
	useEffect(() => {
		const fetchDocPersona = async () => {
			if (!token || !repoFullName) return;

			setIsLoadingPersona(true);
			try {
				const apiBase = BACKEND_URL.endsWith("/api/v1")
					? BACKEND_URL
					: `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;

				const response = await fetch(
					`${apiBase}/repositories/${encodeURIComponent(
						repoFullName
					)}/doc-persona`,
					{
						headers: {
							Authorization: `Bearer ${token}`,
						},
					}
				);

				if (response.ok) {
					const data = await response.json();
					console.log(
						`📋 Fetched doc_persona for ${repoFullName}:`,
						data.doc_persona
					);
					setDocPersona(data.doc_persona || propDocPersona);
				}
			} catch (err) {
				console.error("Error fetching doc_persona:", err);
				// Fall back to prop value
				setDocPersona(propDocPersona);
			} finally {
				setIsLoadingPersona(false);
			}
		};

		fetchDocPersona();
	}, [repoFullName, token, propDocPersona]);

	const handleGenerate = async () => {
		if (disabled) {
			return;
		}

		if (!token) {
			setError("Authentication required to generate docs");
			return;
		}

		setIsGenerating(true);
		setError(null);
		setSuccess(false);

		try {
			onGenerationStart?.();

			console.log(
				`🚀 Generating docs for ${repoFullName} with persona: ${docPersona}`
			);
			const response = await fetch("/api/generate-docs", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${token}`,
				},
				body: JSON.stringify({
					repoName: repoFullName,
					repoShortName: repoName,
					docPersona,
				}),
			});

			if (!response.ok) {
				const errorData = await response.json();

				// =====================================================================
				// PHASE 4 INTEGRATION: Graceful Failure for Usage Limits
				// =====================================================================
				// Check if this is a 403 usage limit exceeded error
				if (
					response.status === 403 &&
					errorData.detail?.error === "usage_limit_exceeded"
				) {
					// Store the detailed error for the upgrade modal
					setUsageLimitError(errorData.detail as UsageLimitError);
					// Don't show generic error message
					return;
				}
				// =====================================================================

				throw new Error(errorData.error || "Failed to generate docs");
			}

			setSuccess(true);
			onGenerationComplete?.();

			// Reset success message after 3 seconds
			setTimeout(() => setSuccess(false), 3000);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Unknown error");
		} finally {
			setIsGenerating(false);
		}
	};

	if (disabled) {
		return (
			<div
				className={`flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300 ${
					fullWidth ? "w-full" : ""
				}`}
			>
				<button
					type="button"
					disabled
					className={`flex items-center space-x-2 px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 cursor-not-allowed ${
						fullWidth ? "w-full justify-center" : ""
					}`}
				>
					<Zap className="w-4 h-4" />
					<span>Generate Docs</span>
				</button>
				{disabledReason && (
					<span className="leading-snug">{disabledReason}</span>
				)}
			</div>
		);
	}

	if (isGenerating) {
		return (
			<div
				className={`flex items-center space-x-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-700 rounded-md text-sm text-blue-700 dark:text-blue-300 ${
					fullWidth ? "w-full justify-center" : ""
				}`}
			>
				<Loader2 className="w-4 h-4 animate-spin" />
				<span>Generating...</span>
			</div>
		);
	}

	if (success) {
		return (
			<div
				className={`flex items-center space-x-2 px-3 py-1.5 bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 rounded-md text-sm text-green-700 dark:text-green-300 ${
					fullWidth ? "w-full justify-center" : ""
				}`}
			>
				<CheckCircle className="w-4 h-4" />
				<span>Docs Generated!</span>
			</div>
		);
	}

	// ========================================================================
	// PHASE 4 INTEGRATION: Usage Limit Exceeded Modal
	// ========================================================================
	if (usageLimitError) {
		return (
			<div className="space-y-3">
				<div
					className={`p-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border-2 border-purple-300 dark:border-purple-700 rounded-lg ${
						fullWidth ? "w-full" : ""
					}`}
				>
					<div className="flex items-start gap-3">
						<AlertCircle className="w-5 h-5 text-purple-600 dark:text-purple-400 flex-shrink-0 mt-0.5" />
						<div className="flex-1 space-y-2">
							<h4 className="font-semibold text-purple-900 dark:text-purple-100 text-sm">
								Usage Limit Reached
							</h4>
							<p className="text-xs text-purple-700 dark:text-purple-300">
								{usageLimitError.message}
							</p>
							<div className="flex items-center gap-2 text-xs text-purple-600 dark:text-purple-400">
								<span className="font-medium">
									Plan:{" "}
									<span className="capitalize">{usageLimitError.plan}</span>
								</span>
								<span>•</span>
								<span>
									{usageLimitError.used} / {usageLimitError.limit} used
								</span>
							</div>
						</div>
					</div>

					<div className="mt-4 flex gap-2">
						<button
							onClick={() => (window.location.href = "/pricing")}
							className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-md text-sm font-medium transition-all shadow-sm hover:shadow-md"
						>
							<ArrowUpCircle className="w-4 h-4" />
							Upgrade to {usageLimitError.plan === "free" ? "Pro" : "Team"}
						</button>
						<button
							onClick={() => setUsageLimitError(null)}
							className="px-4 py-2 border border-purple-300 dark:border-purple-700 text-purple-700 dark:text-purple-300 rounded-md text-sm font-medium hover:bg-purple-50 dark:hover:bg-purple-900/20 transition-colors"
						>
							Dismiss
						</button>
					</div>
				</div>
			</div>
		);
	}
	// ========================================================================

	if (error) {
		return (
			<div
				className={`flex items-center space-x-2 px-3 py-1.5 bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded-md text-sm text-red-700 dark:text-red-300 ${
					fullWidth ? "w-full justify-center" : ""
				}`}
			>
				<AlertCircle className="w-4 h-4" />
				<span>{error}</span>
				<button
					type="button"
					onClick={() => setError(null)}
					className="ml-2 text-xs underline"
				>
					Dismiss
				</button>
			</div>
		);
	}

	return (
		<button
			onClick={handleGenerate}
			disabled={isGenerating}
			className={`flex cursor-pointer items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
				fullWidth ? "w-full justify-center" : ""
			} ${
				hasDocsFolder
					? "bg-purple-50 dark:bg-purple-900/20 border border-purple-300 dark:border-purple-700 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/40"
					: "bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-100 dark:hover:bg-yellow-900/40"
			} disabled:opacity-50 disabled:cursor-not-allowed`}
		>
			{hasDocsFolder ? (
				<>
					<RefreshCw className="w-4 h-4" />
					<span>Regenerate Docs</span>
				</>
			) : (
				<>
					<Zap className="w-4 h-4" />
					<span>Generate Docs</span>
				</>
			)}
		</button>
	);
}
