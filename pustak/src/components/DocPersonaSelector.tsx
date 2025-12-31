"use client";

import { useState, useEffect, useMemo } from "react";
import { BookOpen, Users, Save, Loader2, Sparkles } from "lucide-react";

interface DocPersonaSelectorProps {
  repoId: string;
  onSave?: (persona: string) => void;
  backendUrl?: string;
  userToken?: string;
}

export default function DocPersonaSelector({
  repoId,
  onSave,
  backendUrl = "http://localhost:8000",
  userToken,
}: DocPersonaSelectorProps) {
  // Extract actual repo name if it contains org/repo format
  const normalizedRepoId = useMemo(() => {
    console.log('🔍 DocPersonaSelector received repoId:', repoId);
    
    // If repoId is in the format "org/repo", use it directly
    if (repoId && repoId.includes('/')) {
      return repoId;
    }
    
    // If repoId has multiple segments (like org/repo/settings), extract org/repo
    const segments = repoId.split('/');
    if (segments.length >= 2) {
      const result = `${segments[0]}/${segments[1]}`;
      console.log('🔍 Normalized repoId to:', result);
      return result;
    }
    
    return repoId;
  }, [repoId]);
  const [selectedPersona, setSelectedPersona] = useState<string>("internal");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const apiBase = useMemo(() => {
    const normalized = backendUrl.replace(/\/$/, "");
    const hasApiSuffix = /\/api(\/v\d+)?$/i.test(normalized);
    return hasApiSuffix ? normalized : `${normalized}/api/v1`;
  }, [backendUrl]);

  // Fetch current doc_persona
  useEffect(() => {
    const fetchPersona = async () => {
      if (!userToken) return;

      setLoading(true);
      try {
        const response = await fetch(
          `${apiBase}/repositories/${encodeURIComponent(normalizedRepoId)}/doc-persona`,
          {
            headers: {
              Authorization: `Bearer ${userToken}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          setSelectedPersona(data.doc_persona || "internal");
        }
      } catch (err) {
        console.error("Error fetching doc_persona:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchPersona();
  }, [normalizedRepoId, userToken, apiBase]);

  const handleSave = async () => {
    if (!userToken) {
      setError("Not authenticated");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await fetch(
        `${apiBase}/repositories/${encodeURIComponent(
          normalizedRepoId
        )}/doc-persona?doc_persona=${encodeURIComponent(selectedPersona)}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${userToken}`,
          },
        }
      );

      if (response.ok) {
        setSuccess(true);
        onSave?.(selectedPersona);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to save doc_persona");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error saving doc_persona");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-3xl border border-slate-900/50 bg-slate-950/70 p-8 shadow-lg shadow-blue-950/30">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-transparent to-purple-500/10 opacity-40" aria-hidden />
      <div className="relative space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.32em] text-blue-200">
              Persona
            </div>
            <h3 className="mt-3 text-xl font-semibold text-slate-100">Documentation persona</h3>
            <p className="mt-2 text-sm text-slate-400">
              Choose the voice Pustak should adopt for this repository.
            </p>
          </div>
          <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-blue-500/40 bg-blue-500/10 text-blue-200">
            <Sparkles className="h-5 w-5" />
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {[{
            value: "internal",
            title: "Internal",
            description: "Deep dive for staff engineers—architecture, implementation detail, and workflow nuance.",
            icon: BookOpen,
            accent: "from-blue-400/30",
          }, {
            value: "developer",
            title: "Developer",
            description: "External-friendly docs focusing on APIs, usage stories, and integration paths.",
            icon: Users,
            accent: "from-emerald-400/30",
          }].map((option) => {
            const OptionIcon = option.icon;
            const isSelected = selectedPersona === option.value;
            return (
              <label
                key={option.value}
                className={`group relative cursor-pointer overflow-hidden rounded-2xl border p-5 transition duration-300 ${
                  isSelected
                    ? "border-blue-400/60 bg-slate-900/80"
                    : "border-slate-800/80 bg-slate-950/60 hover:border-blue-300/40 hover:bg-slate-950/70"
                }`}
              >
                <div className={`absolute inset-0 bg-gradient-to-br ${option.accent} via-transparent to-transparent opacity-0 transition duration-500 group-hover:opacity-60 ${isSelected ? "opacity-70" : ""}`} aria-hidden />
                <input
                  type="radio"
                  name="persona"
                  value={option.value}
                  checked={isSelected}
                  onChange={(event) => setSelectedPersona(event.target.value)}
                  className="sr-only"
                />
                <div className="relative flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`flex h-9 w-9 items-center justify-center rounded-xl border border-blue-400/30 bg-blue-500/10 text-blue-100 transition ${isSelected ? "scale-105" : "opacity-70"}`}>
                        <OptionIcon className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-slate-100">{option.title}</p>
                        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{option.value === "internal" ? "In-depth" : "External"}</p>
                      </div>
                    </div>
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded-full border ${
                        isSelected
                          ? "border-blue-300 bg-blue-400/90"
                          : "border-slate-700 bg-slate-900"
                      }`}
                    >
                      <span className={`h-2.5 w-2.5 rounded-full bg-white transition ${isSelected ? "opacity-100" : "opacity-0"}`} />
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">{option.description}</p>
                </div>
              </label>
            );
          })}
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-2xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {error}
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
            ✅ Documentation persona updated
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          className="group inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-blue-500/50 bg-blue-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save documentation persona
            </>
          )}
        </button>
      </div>
    </div>
  );
}
