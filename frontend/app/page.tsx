"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Tag = {
  id: number;
  name: string;
};

type CheckResult = {
  quantity: number | null;
  unit: string | null;
  name: string;
  status: string;
  matched_tags: string[];
  substitute: { name: string; note: string | null } | null;
};

const STATUS_STYLES: Record<string, string> = {
  flagged: "bg-red-50 border-red-300 text-red-900",
  safe: "bg-green-50 border-green-300 text-green-900",
  unrecognized: "bg-gray-50 border-gray-300 text-gray-700",
};

const STATUS_LABELS: Record<string, string> = {
  flagged: "Flagged",
  safe: "Safe",
  unrecognized: "Unrecognized",
};

export default function Home() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [rawText, setRawText] = useState("");
  const [results, setResults] = useState<CheckResult[] | null>(null);

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [title, setTitle] = useState("");
  const [saveState, setSaveState] = useState<
    { status: "idle" } | { status: "saving" } | { status: "saved"; recipeId: number } | { status: "error"; message: string }
  >({ status: "idle" });

  useEffect(() => {
    async function fetchTags() {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/ingredient-tags`);
      const data = await res.json();
      setTags(data);
    }

    fetchTags();
  }, []);

  useEffect(() => {
    async function fetchAccountRestrictions() {
      const meRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/me`, {
        credentials: "include",
      });

      if (!meRes.ok) {
        setIsLoggedIn(false);
        return;
      }

      setIsLoggedIn(true);

      const restrictionsRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/me/restrictions`,
        { credentials: "include" }
      );

      if (restrictionsRes.ok) {
        const data = await restrictionsRes.json();
        setSelectedTagIds(data.tag_ids);
      }
    }

    fetchAccountRestrictions();
  }, []);

  function toggleTag(tagId: number) {
    const next = selectedTagIds.includes(tagId)
      ? selectedTagIds.filter((id) => id !== tagId)
      : [...selectedTagIds, tagId];

    setSelectedTagIds(next);

    if (isLoggedIn) {
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/me/restrictions`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ tag_ids: next }),
      });
    }
  }

  async function handleCheck() {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/check-recipe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText, active_tag_ids: selectedTagIds }),
    });

    const data = await res.json();
    setResults(data);
    setSaveState({ status: "idle" });
  }

  async function handleSave() {
    setSaveState({ status: "saving" });

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/recipes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ title: title.trim() || null, raw_text: rawText }),
    });

    if (!res.ok) {
      setSaveState({ status: "error", message: "Couldn't save this recipe. Try again." });
      return;
    }

    const data = await res.json();
    setSaveState({ status: "saved", recipeId: data.recipe_id });
  }

  return (
    <main className="max-w-2xl mx-auto mt-12 px-6">
      <h1 className="text-2xl font-semibold mb-6">Check a recipe</h1>

      <h2 className="font-medium mb-2">
        Your restrictions
        {isLoggedIn && (
          <span className="text-xs font-normal text-gray-500 ml-2">
            (synced with your account)
          </span>
        )}
      </h2>
      <div className="flex flex-wrap gap-3 mb-6">
        {tags.map((tag) => (
          <label key={tag.id} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={selectedTagIds.includes(tag.id)}
              onChange={() => toggleTag(tag.id)}
            />
            {tag.name}
          </label>
        ))}
      </div>

      <h2 className="font-medium mb-2">Recipe</h2>
      <textarea
        value={rawText}
        onChange={(e) => setRawText(e.target.value)}
        rows={8}
        placeholder="Paste your recipe here, one ingredient per line..."
        className="w-full border rounded px-3 py-2 mb-4"
      />

      <button
        onClick={handleCheck}
        className="bg-black text-white rounded px-4 py-2 mb-6"
      >
        Check recipe
      </button>

      {results && (
        <div>
          <h2 className="font-medium mb-2">Results</h2>
          <div className="space-y-3 mb-6">
            {results.map((r, i) => (
              <div
                key={i}
                className={`border rounded px-4 py-3 ${
                  STATUS_STYLES[r.status] ?? STATUS_STYLES.unrecognized
                }`}
              >
                <div className="flex justify-between items-start gap-4">
                  <span className="font-medium">
                    {r.quantity !== null ? `${r.quantity} ` : ""}
                    {r.unit ? `${r.unit} ` : ""}
                    {r.name}
                  </span>
                  <span className="text-xs font-semibold uppercase tracking-wide shrink-0">
                    {STATUS_LABELS[r.status] ?? r.status}
                  </span>
                </div>

                {r.status === "flagged" && r.matched_tags.length > 0 && (
                  <p className="text-sm mt-1">
                    Conflicts with: {r.matched_tags.join(", ")}
                  </p>
                )}

                {r.substitute && (
                  <p className="text-sm mt-2">
                    Try instead:{" "}
                    <span className="font-medium">{r.substitute.name}</span>
                    {r.substitute.note && ` — ${r.substitute.note}`}
                  </p>
                )}
              </div>
            ))}
          </div>

          {isLoggedIn ? (
            saveState.status === "saved" ? (
              <p className="text-sm">
                Saved.{" "}
                <Link href={`/recipes/${saveState.recipeId}`} className="underline">
                  View in history
                </Link>
              </p>
            ) : (
              <div className="flex flex-wrap items-center gap-3">
                <input
                  type="text"
                  placeholder="Recipe title (optional)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="border rounded px-3 py-2 text-sm"
                />
                <button
                  onClick={handleSave}
                  disabled={saveState.status === "saving"}
                  className="border rounded px-4 py-2 text-sm disabled:opacity-50"
                >
                  {saveState.status === "saving" ? "Saving..." : "Save recipe"}
                </button>
                {saveState.status === "error" && (
                  <p className="text-sm text-red-600">{saveState.message}</p>
                )}
              </div>
            )
          ) : (
            <p className="text-sm text-gray-500">
              <Link href="/login" className="underline">
                Log in
              </Link>{" "}
              to save this recipe and build a history.
            </p>
          )}
        </div>
      )}
    </main>
  );
}
