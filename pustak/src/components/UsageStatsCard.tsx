"use client";

/**
 * Usage Stats Card Component - Phase 4: Frontend Integration
 * ===========================================================
 *
 * Displays current billing cycle usage and limits with visual
 * progress bars and warnings when approaching limits.
 *
 * Features:
 * - Real-time usage tracking
 * - Color-coded progress bars (green/yellow/red)
 * - Warnings at 80%+ usage
 * - Upgrade CTAs when needed
 * - Cycle end date display
 */

import { useState, useEffect } from "react";
import {
	TrendingUp,
	AlertTriangle,
	CheckCircle,
	ArrowUpCircle,
	Loader2,
	Calendar,
	Zap,
} from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import {
	fetchUsageStats,
	getUsagePercentage,
	getUsageColor,
	formatNumber,
	formatDate,
	type UsageStats,
	type ResourceUsage,
} from "@/lib/usage";

interface UsageStatsCardProps {
	/**
	 * Show compact version (only docs_generated)
	 * Default: false (shows all resources)
	 */
	compact?: boolean;

	/**
	 * Callback when user clicks "Upgrade" button
	 */
	onUpgradeClick?: () => void;

	/**
	 * Custom class name for container
	 */
	className?: string;
}

/**
 * Single resource usage progress bar
 */
interface ResourceProgressBarProps {
	label: string;
	usage: ResourceUsage;
	icon?: React.ReactNode;
}

function ResourceProgressBar({ label, usage, icon }: ResourceProgressBarProps) {
	const percentage = getUsagePercentage(usage.used, usage.limit);
	const color = getUsageColor(percentage);

	// Color classes mapping
	const colorClasses = {
		green: {
			bg: "bg-green-500",
			text: "text-green-700 dark:text-green-300",
			border: "border-green-200 dark:border-green-700",
			lightBg: "bg-green-50 dark:bg-green-900/20",
		},
		yellow: {
			bg: "bg-yellow-500",
			text: "text-yellow-700 dark:text-yellow-300",
			border: "border-yellow-200 dark:border-yellow-700",
			lightBg: "bg-yellow-50 dark:bg-yellow-900/20",
		},
		red: {
			bg: "bg-red-500",
			text: "text-red-700 dark:text-red-300",
			border: "border-red-200 dark:border-red-700",
			lightBg: "bg-red-50 dark:bg-red-900/20",
		},
	};

	const colors = colorClasses[color];

	return (
		<div className="space-y-2">
			{/* Header */}
			<div className="flex items-center justify-between text-sm">
				<div className="flex items-center gap-2">
					{icon}
					<span className="font-medium text-gray-700 dark:text-gray-200">
						{label}
					</span>
				</div>
				<span className={`font-semibold ${colors.text}`}>
					{formatNumber(usage.used)} / {formatNumber(usage.limit)}
				</span>
			</div>

			{/* Progress Bar */}
			<div className="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
				<div
					className={`absolute left-0 top-0 h-full ${colors.bg} transition-all duration-300`}
					style={{
						width: percentage !== null ? `${percentage}%` : "0%",
					}}
				/>
			</div>

			{/* Percentage & Warning */}
			<div className="flex items-center justify-between text-xs">
				<span className="text-gray-600 dark:text-gray-400">
					{percentage !== null ? `${percentage.toFixed(1)}% used` : "Unlimited"}
				</span>

				{percentage !== null && percentage >= 90 && (
					<span
						className={`flex items-center gap-1 ${colors.text} font-medium`}
					>
						<AlertTriangle className="w-3 h-3" />
						Running Low
					</span>
				)}

				{percentage !== null && percentage >= 80 && percentage < 90 && (
					<span
						className={`flex items-center gap-1 ${colors.text} font-medium`}
					>
						<TrendingUp className="w-3 h-3" />
						Nearing Limit
					</span>
				)}

				{(percentage === null || percentage < 80) && usage.allowed && (
					<span className="flex items-center gap-1 text-green-600 dark:text-green-400 font-medium">
						<CheckCircle className="w-3 h-3" />
						Good
					</span>
				)}
			</div>
		</div>
	);
}

/**
 * Main usage stats card component
 */
export function UsageStatsCard({
	compact = false,
	onUpgradeClick,
	className = "",
}: UsageStatsCardProps) {
	const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const { token } = useAuth();

	// Fetch usage stats
	useEffect(() => {
		const loadUsageStats = async () => {
			if (!token) {
				setIsLoading(false);
				setError("Not authenticated");
				return;
			}

			try {
				setIsLoading(true);
				setError(null);
				const data = await fetchUsageStats(token);
				setUsageStats(data);
			} catch (err) {
				console.error("Failed to load usage stats:", err);
				setError(err instanceof Error ? err.message : "Failed to load usage");
			} finally {
				setIsLoading(false);
			}
		};

		loadUsageStats();

		// Refresh every 30 seconds
		const interval = setInterval(loadUsageStats, 30000);
		return () => clearInterval(interval);
	}, [token]);

	// Loading state
	if (isLoading) {
		return (
			<div
				className={`border border-gray-200 dark:border-gray-700 rounded-lg p-6 ${className}`}
			>
				<div className="flex items-center justify-center py-8">
					<Loader2 className="w-6 h-6 animate-spin text-gray-400" />
				</div>
			</div>
		);
	}

	// Error state
	if (error || !usageStats) {
		return (
			<div
				className={`border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 rounded-lg p-6 ${className}`}
			>
				<div className="flex items-center gap-2 text-red-700 dark:text-red-300">
					<AlertTriangle className="w-5 h-5" />
					<span className="text-sm">
						{error || "Could not load usage stats"}
					</span>
				</div>
			</div>
		);
	}

	// Check if nearing any limit
	const nearingLimit = Object.values(usageStats.limits).some((limit) => {
		if (!limit) return false;
		const percentage = getUsagePercentage(limit.used, limit.limit);
		return percentage !== null && percentage >= 80;
	});

	// Check if at any limit
	const atLimit = Object.values(usageStats.limits).some((limit) => {
		return limit && !limit.allowed;
	});

	return (
		<div
			className={`border border-gray-200 dark:border-gray-700 rounded-lg p-6 space-y-6 ${className}`}
		>
			{/* Header */}
			<div className="flex items-center justify-between">
				<div>
					<h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
						Usage & Limits
					</h3>
					<p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
						Plan:{" "}
						<span className="font-medium capitalize">{usageStats.plan}</span>
					</p>
				</div>

				{/* Cycle end date */}
				<div className="text-right">
					<div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
						<Calendar className="w-3 h-3" />
						<span>Resets</span>
					</div>
					<p className="text-sm font-medium text-gray-700 dark:text-gray-300 mt-1">
						{formatDate(usageStats.cycle_end)}
					</p>
				</div>
			</div>

			{/* Usage Bars */}
			<div className="space-y-4">
				{/* Documents Generated (Always show) */}
				{usageStats.limits.docs_generated && (
					<ResourceProgressBar
						label="Documents Generated"
						usage={usageStats.limits.docs_generated}
						icon={<Zap className="w-4 h-4 text-purple-500" />}
					/>
				)}

				{/* Other resources (only in non-compact mode) */}
				{!compact && (
					<>
						{usageStats.limits.repos_connected && (
							<ResourceProgressBar
								label="Repositories Connected"
								usage={usageStats.limits.repos_connected}
								icon={<TrendingUp className="w-4 h-4 text-blue-500" />}
							/>
						)}

						{usageStats.limits.api_calls && (
							<ResourceProgressBar
								label="API Calls"
								usage={usageStats.limits.api_calls}
								icon={<TrendingUp className="w-4 h-4 text-green-500" />}
							/>
						)}
					</>
				)}
			</div>

			{/* Warning/Upgrade CTA */}
			{atLimit && (
				<div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-md space-y-3">
					<div className="flex items-start gap-2">
						<AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
						<div className="flex-1">
							<h4 className="font-semibold text-red-900 dark:text-red-100 text-sm">
								Limit Reached
							</h4>
							<p className="text-xs text-red-700 dark:text-red-300 mt-1">
								You've reached your plan's limit. Upgrade to continue using
								Pustak.
							</p>
						</div>
					</div>

					<button
						onClick={
							onUpgradeClick || (() => (window.location.href = "/pricing"))
						}
						className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium transition-colors"
					>
						<ArrowUpCircle className="w-4 h-4" />
						Upgrade Plan
					</button>
				</div>
			)}

			{nearingLimit && !atLimit && (
				<div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-md space-y-3">
					<div className="flex items-start gap-2">
						<TrendingUp className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
						<div className="flex-1">
							<h4 className="font-semibold text-yellow-900 dark:text-yellow-100 text-sm">
								Approaching Limit
							</h4>
							<p className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
								You're using over 80% of your quota. Consider upgrading soon.
							</p>
						</div>
					</div>

					<button
						onClick={
							onUpgradeClick || (() => (window.location.href = "/pricing"))
						}
						className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium transition-colors"
					>
						<ArrowUpCircle className="w-4 h-4" />
						View Plans
					</button>
				</div>
			)}
		</div>
	);
}
