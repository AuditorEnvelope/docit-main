"use client";

import { useState, useEffect } from "react";
import { BookOpen, Users, Save, Loader2 } from "lucide-react";

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
  const [selectedPersona, setSelectedPersona] = useState<string>("internal");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Fetch current doc_persona
  useEffect(() => {
    const fetchPersona = async () => {
      if (!userToken) return;

      setLoading(true);
      try {
        const response = await fetch(
          `${backendUrl}/api/repositories/${encodeURIComponent(repoId)}/doc-persona`,
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
  }, [repoId, userToken, backendUrl]);

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
        `${backendUrl}/api/repositories/${encodeURIComponent(repoId)}/doc-persona`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${userToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ doc_persona: selectedPersona }),
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
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
        Documentation Persona
      </h3>

      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Choose the documentation style for this repository:
      </p>

      <div className="space-y-3 mb-6">
        {/* Internal Option */}
        <label className="flex items-start p-4 border-2 rounded-lg cursor-pointer transition-all"
          style={{
            borderColor: selectedPersona === "internal" ? "#3b82f6" : "#e5e7eb",
            backgroundColor: selectedPersona === "internal" ? "#eff6ff" : "transparent",
          }}>
          <input
            type="radio"
            name="persona"
            value="internal"
            checked={selectedPersona === "internal"}
            onChange={(e) => setSelectedPersona(e.target.value)}
            className="mt-1 mr-3"
          />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-blue-600" />
              <span className="font-semibold text-gray-900 dark:text-white">
                Internal
              </span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Detailed documentation for staff engineers. Includes internal architecture,
              implementation details, and advanced workflows.
            </p>
          </div>
        </label>

        {/* Developer Option */}
        <label className="flex items-start p-4 border-2 rounded-lg cursor-pointer transition-all"
          style={{
            borderColor: selectedPersona === "developer" ? "#3b82f6" : "#e5e7eb",
            backgroundColor: selectedPersona === "developer" ? "#eff6ff" : "transparent",
          }}>
          <input
            type="radio"
            name="persona"
            value="developer"
            checked={selectedPersona === "developer"}
            onChange={(e) => setSelectedPersona(e.target.value)}
            className="mt-1 mr-3"
          />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-green-600" />
              <span className="font-semibold text-gray-900 dark:text-white">
                Developer
              </span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Public-safe documentation for external partners. Focuses on APIs, usage examples,
              and integration guides. Excludes sensitive information.
            </p>
          </div>
        </label>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-red-700 dark:text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded text-green-700 dark:text-green-400 text-sm">
          ✅ Documentation persona updated successfully!
        </div>
      )}

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
      >
        {saving ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Saving...
          </>
        ) : (
          <>
            <Save className="w-4 h-4" />
            Save Documentation Persona
          </>
        )}
      </button>
    </div>
  );
}
