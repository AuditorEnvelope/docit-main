"use client";

import { useState, useEffect, useCallback } from "react";
import {
	X,
	Loader2,
	CheckCircle2,
	AlertCircle,
	ExternalLink,
	Download,
} from "lucide-react";

interface ConnectOrganizationModalProps {
	isOpen: boolean;
	onClose: () => void;
	backendUrl: string;
	userToken: string;
	onSuccess?: () => void;
}

interface OrgStatus {
	org: string;
	appInstalled: boolean;
	connected: boolean;
}

interface Organization {
	id: string;
	login: string;
	avatar_url: string;
}

export default function ConnectOrganizationModal({
	isOpen,
	onClose,
	backendUrl,
	userToken,
	onSuccess,
}: ConnectOrganizationModalProps) {
	const [organizations, setOrganizations] = useState<Organization[]>([]);
	const [selectedOrg, setSelectedOrg] = useState<string>("");
	const [orgStatus, setOrgStatus] = useState<OrgStatus | null>(null);
	const [loading, setLoading] = useState(false);
	const [checkingApp, setCheckingApp] = useState(false);
	const [pollingAppInstall, setPollingAppInstall] = useState(false);
	const [error, setError] = useState<string>("");
	const [success, setSuccess] = useState(false);

	useEffect(() => {
		if (isOpen) {
			fetchOrganizations();
		}
	}, [isOpen]);

	useEffect(() => {
		if (selectedOrg) {
			checkAppInstallation(selectedOrg);
		}
	}, [selectedOrg]);

	const fetchOrganizations = async () => {
		setLoading(true);
		setError("");
		try {
			const response = await fetch(`/api/user/organizations`, {
				headers: {
					Authorization: `Bearer ${userToken}`,
				},
			});

			if (response.ok) {
				const data = await response.json();
				setOrganizations((data.organizations || []) as Organization[]);
			} else {
				setError("Failed to fetch organizations");
			}
		} catch (err) {
			setError("Error connecting to server");
			console.error(err);
		} finally {
			setLoading(false);
		}
	};

	const checkAppInstallation = useCallback(
		async (orgId: string) => {
			setCheckingApp(true);
			try {
				const response = await fetch(`${backendUrl}/org/${orgId}/verify-apps`, {
					headers: {
						Authorization: `Bearer ${userToken}`,
					},
				});

				if (response.ok) {
					const data = await response.json();
					const readerInstalled = data?.reader_app?.installed === true;
					const writerInstalled = data?.writer_app?.installed === true;
					setOrgStatus({
						org: orgId,
						appInstalled: readerInstalled,
						connected: readerInstalled && writerInstalled,
					});
					if (readerInstalled) {
						setPollingAppInstall(false);
					}
				} else {
					setOrgStatus({
						org: orgId,
						appInstalled: false,
						connected: false,
					});
				}
			} catch (err) {
				console.error("Error checking app installation:", err);
				setOrgStatus({
					org: orgId,
					appInstalled: false,
					connected: false,
				});
			} finally {
				setCheckingApp(false);
			}
		},
		[backendUrl, userToken],
	);

	const handleConnect = async () => {
		if (!selectedOrg) {
			setError("Please select an organization");
			return;
		}

		if (!orgStatus?.appInstalled) {
			setError("Please install the GitHub App first");
			return;
		}

		setLoading(true);
		setError("");
		try {
			const normalizedApiBase = backendUrl.endsWith("/api/v1")
				? backendUrl
				: `${backendUrl.replace(/\/$/, "")}/api/v1`;

			const response = await fetch(`${normalizedApiBase}/webhook/register`, {
				method: "POST",
				headers: {
					Authorization: `Bearer ${userToken}`,
					"Content-Type": "application/json",
				},
				body: JSON.stringify({ org_id: selectedOrg }),
			});

			if (response.ok) {
				setSuccess(true);
				setTimeout(() => {
					onClose();
					setSuccess(false);
					setSelectedOrg("");
					setOrgStatus(null);
					if (onSuccess) {
						onSuccess();
					}
				}, 2500);
			} else {
				const data = await response.json();
				setError(data.detail || "Failed to connect organization");
			}
		} catch (err) {
			setError("Error connecting organization");
			console.error(err);
		} finally {
			setLoading(false);
		}
	};

	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
			<div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl border border-slate-700/50">
				{/* Header */}
				<div className="flex items-center justify-between p-8 border-b border-slate-700/50">
					<div className="flex items-center gap-4">
						<div className="w-12 h-12 bg-gradient-to-br from-purple-500 via-purple-600 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
							<span className="text-white text-xl">⚡</span>
						</div>
						<div>
							<h2 className="text-2xl font-bold text-white">
								Connect Organization
							</h2>
							<p className="text-sm text-slate-400 mt-1">
								Enable automatic documentation generation
							</p>
						</div>
					</div>
					<button
						onClick={onClose}
						className="text-slate-400 hover:text-white transition-colors p-2 hover:bg-slate-700/50 rounded-lg"
					>
						<X size={24} />
					</button>
				</div>

				{/* Content */}
				<div className="p-8 space-y-6">
					{success ? (
						<div className="text-center py-12 space-y-4">
							<div className="flex justify-center">
								<div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center">
									<CheckCircle2 size={40} className="text-green-400" />
								</div>
							</div>
							<div>
								<h3 className="text-2xl font-bold text-white mb-2">
									🎉 Connected Successfully!
								</h3>
								<p className="text-slate-400 text-lg">
									Your organization is now connected. Webhooks will
									automatically generate documentation whenever you push code.
								</p>
							</div>
						</div>
					) : (
						<div className="space-y-6">
							{/* Step 1: Select Organization */}
							<div className="space-y-3">
								<div className="flex items-center gap-2 mb-4">
									<div className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-500/50 flex items-center justify-center text-purple-400 font-bold text-sm">
										1
									</div>
									<label className="text-lg font-semibold text-white">
										Select Your Organization
									</label>
								</div>
								<select
									value={selectedOrg}
									onChange={(e) => setSelectedOrg(e.target.value)}
									disabled={loading || organizations.length === 0}
									className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-base"
								>
									<option value="">-- Select your organization --</option>
									{organizations.map((org) => (
										<option key={org.id} value={org.login}>
											{org.login}
										</option>
									))}
								</select>
								{organizations.length === 0 && !loading && (
									<p className="text-sm text-amber-400/80 flex items-center gap-2 mt-2">
										<AlertCircle size={16} />
										No organizations found. Make sure you're a member of at
										least one.
									</p>
								)}
							</div>

							{/* Step 2: App Installation Status */}
							{selectedOrg && (
								<div className="space-y-3">
									<div className="flex items-center gap-2 mb-4">
										<div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500/50 flex items-center justify-center text-blue-400 font-bold text-sm">
											2
										</div>
										<label className="text-lg font-semibold text-white">
											GitHub App Installation
										</label>
									</div>

									{checkingApp ? (
										<div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 flex items-center justify-between gap-3">
											<div className="flex items-center gap-3">
												<Loader2
													size={20}
													className="text-blue-400 animate-spin"
												/>
												<span className="text-slate-300">
													Checking app installation...
												</span>
											</div>
											{pollingAppInstall && (
												<span className="text-xs text-slate-400">
													Auto-refreshing
												</span>
											)}
										</div>
									) : orgStatus?.appInstalled ? (
										<div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 flex items-start gap-3">
											<CheckCircle2
												size={20}
												className="text-green-400 mt-0.5 flex-shrink-0"
											/>
											<div>
												<p className="font-semibold text-green-300">
													✓ App Installed
												</p>
												<p className="text-sm text-green-200/80 mt-1">
													DocIt Analyser AI is installed in this organization.
													You can now proceed to connect.
												</p>
											</div>
										</div>
									) : (
										<div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 space-y-3">
											<div className="flex items-start gap-3">
												<AlertCircle
													size={20}
													className="text-amber-400 mt-0.5 flex-shrink-0"
												/>
												<div>
													<p className="font-semibold text-amber-300">
														App Not Installed
													</p>
													<p className="text-sm text-amber-200/80 mt-1">
														Install the <strong>DocIt Analyser AI</strong>{" "}
														GitHub App in <strong>{selectedOrg}</strong> to
														enable automatic webhook registration for repository
														reads.
													</p>
												</div>
											</div>
											<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
												<a
													href="https://github.com/apps/pustak-analyser-ai-test"
													target="_blank"
													rel="noopener noreferrer"
													onClick={() => setPollingAppInstall(true)}
													className="inline-flex items-center gap-2 px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-semibold transition-colors"
												>
													<Download size={16} />
													Install DocIt Analyser AI
													<ExternalLink size={14} />
												</a>
												<button
													onClick={() => {
														if (selectedOrg) {
															setPollingAppInstall(true);
															checkAppInstallation(selectedOrg);
														}
													}}
													className="inline-flex items-center gap-2 px-4 py-2.5 border border-amber-500/50 text-amber-200 rounded-lg text-sm font-semibold transition-colors hover:bg-amber-500/20"
												>
													<Loader2
														size={14}
														className={`$${"{"}pollingAppInstall ? "animate-spin" : ""${"}"}`}
													/>
													Refresh status
												</button>
											</div>
										</div>
									)}
								</div>
							)}

							{/* Step 3: How it Works */}
							<div className="space-y-3">
								<div className="flex items-center gap-2 mb-4">
									<div className="w-8 h-8 rounded-full bg-green-500/20 border border-green-500/50 flex items-center justify-center text-green-400 font-bold text-sm">
										3
									</div>
									<label className="text-lg font-semibold text-white">
										How It Works
									</label>
								</div>
								<div className="bg-gradient-to-br from-purple-500/10 via-blue-500/10 to-cyan-500/10 border border-purple-500/20 rounded-xl p-4 space-y-2">
									<p className="text-sm text-slate-300 flex items-start gap-2">
										<span className="text-purple-400 font-bold mt-0.5">→</span>
										<span>Install the GitHub App in your organization</span>
									</p>
									<p className="text-sm text-slate-300 flex items-start gap-2">
										<span className="text-blue-400 font-bold mt-0.5">→</span>
										<span>Select your organization and click "Connect"</span>
									</p>
									<p className="text-sm text-slate-300 flex items-start gap-2">
										<span className="text-cyan-400 font-bold mt-0.5">→</span>
										<span>Webhooks are automatically registered</span>
									</p>
									<p className="text-sm text-slate-300 flex items-start gap-2">
										<span className="text-green-400 font-bold mt-0.5">→</span>
										<span>
											Documentation generates automatically on every push!
										</span>
									</p>
								</div>
							</div>

							{/* Error Message */}
							{error && (
								<div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
									<AlertCircle
										size={20}
										className="text-red-400 mt-0.5 flex-shrink-0"
									/>
									<p className="text-sm text-red-300">{error}</p>
								</div>
							)}
						</div>
					)}
				</div>

				{/* Footer */}
				{!success && (
					<div className="flex gap-3 p-8 border-t border-slate-700/50 bg-slate-800/30">
						<button
							onClick={onClose}
							disabled={loading}
							className="flex-1 px-6 py-3 bg-slate-700/50 hover:bg-slate-700 text-white rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-slate-600/50"
						>
							Cancel
						</button>
						<button
							onClick={handleConnect}
							disabled={
								loading ||
								!selectedOrg ||
								!orgStatus?.appInstalled ||
								organizations.length === 0
							}
							className="flex-1 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
						>
							{loading ? (
								<>
									<Loader2 size={18} className="animate-spin" />
									Connecting...
								</>
							) : (
								<>
									<span>🔗</span>
									Connect Organization
								</>
							)}
						</button>
					</div>
				)}
			</div>
		</div>
	);
}
