"use client";

import { useEffect, useRef, useState } from "react";
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

type RecipeMeta = {
  title: string;
  image_url: string | null;
  source_url: string | null;
};

// Photos from a phone can be 5-10 MB. The server accepts up to 8 MB and OCR
// gains nothing from more pixels than this, so big photos are shrunk in the
// browser first. If anything goes wrong the original file is sent instead.
const SHRINK_ABOVE_BYTES = 2 * 1024 * 1024;
const MAX_PIXELS = 5_000_000;
const MAX_SIDE = 3000;

async function shrinkImage(file: File): Promise<File> {
  if (file.size <= SHRINK_ABOVE_BYTES) return file;

  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const scale = Math.min(
      1,
      Math.sqrt(MAX_PIXELS / (bitmap.width * bitmap.height)),
      MAX_SIDE / Math.max(bitmap.width, bitmap.height)
    );
    const width = Math.round(bitmap.width * scale);
    const height = Math.round(bitmap.height * scale);

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.85)
    );
    if (!blob || blob.size >= file.size) return file;

    const name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg" });
  } catch {
    return file;
  }
}

const NETWORK_ERROR = "Couldn't reach the server. Check your connection and try again.";

const STATUS_STYLES: Record<string, string> = {
  flagged: "bg-danger-soft border-danger-border text-danger",
  safe: "bg-safe-soft border-safe-border text-safe",
  unrecognized: "bg-warn-soft border-warn-border text-warn",
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

  const [lookupQuery, setLookupQuery] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [recipeMeta, setRecipeMeta] = useState<RecipeMeta | null>(null);

  const [scanLoading, setScanLoading] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [checkError, setCheckError] = useState<string | null>(null);
  const [tagsLoaded, setTagsLoaded] = useState(false);
  const [serverSlow, setServerSlow] = useState(false);

  // The demo runs on free hosting that goes to sleep when idle, so the first
  // request can take up to a minute. Keep trying quietly and say what's going on.
  useEffect(() => {
    let cancelled = false;
    const slowTimer = setTimeout(() => {
      if (!cancelled) setServerSlow(true);
    }, 3000);

    async function fetchTags() {
      for (let attempt = 0; attempt < 20 && !cancelled; attempt++) {
        try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/ingredient-tags`);
          if (res.ok) {
            const data = await res.json();
            if (!cancelled) {
              setTags(data);
              setTagsLoaded(true);
            }
            break;
          }
        } catch {
          // server still waking up or briefly unreachable: try again below
        }
        await new Promise((resolve) => setTimeout(resolve, 4000));
      }
      clearTimeout(slowTimer);
      if (!cancelled) setServerSlow(false);
    }

    fetchTags();
    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, []);

  // Wait until the server has answered once, so the sign-in check doesn't
  // fail while it is still waking up.
  useEffect(() => {
    if (!tagsLoaded) return;

    async function fetchAccountRestrictions() {
      try {
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
      } catch {
        setIsLoggedIn(false);
      }
    }

    fetchAccountRestrictions();
  }, [tagsLoaded]);

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
    setCheckError(null);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/check-recipe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: rawText, active_tag_ids: selectedTagIds }),
      });

      if (!res.ok) {
        setCheckError("Couldn't check that recipe. Try again.");
        return;
      }

      const data = await res.json();
      setResults(data);
      setRecipeMeta(null);
      setSaveState({ status: "idle" });
    } catch {
      setCheckError(NETWORK_ERROR);
    }
  }

  async function handleLookup() {
    if (!lookupQuery.trim()) return;

    setLookupLoading(true);
    setLookupError(null);

    let res: Response;
    try {
      res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/lookup-recipe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: lookupQuery, active_tag_ids: selectedTagIds }),
      });
    } catch {
      setLookupError(NETWORK_ERROR);
      setLookupLoading(false);
      return;
    }

    if (!res.ok) {
      const data = await res.json().catch(() => null);
      setLookupError(data?.detail || "Couldn't find that recipe. Try a different name.");
      setLookupLoading(false);
      return;
    }

    const data = await res.json();
    setRawText(data.raw_text);
    setResults(data.results);
    setRecipeMeta({
      title: data.title,
      image_url: data.image_url,
      source_url: data.source_url,
    });
    setTitle(data.title);
    setSaveState({ status: "idle" });
    setLookupLoading(false);
  }

  async function handleScan(file: File) {
    setScanLoading(true);
    setScanError(null);

    const formData = new FormData();
    formData.append("file", await shrinkImage(file));

    const params = new URLSearchParams();
    selectedTagIds.forEach((id) => params.append("active_tag_ids", String(id)));

    let res: Response;
    try {
      res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/scan-recipe?${params.toString()}`,
        { method: "POST", body: formData }
      );
    } catch {
      setScanError(NETWORK_ERROR);
      setScanLoading(false);
      return;
    }

    if (!res.ok) {
      const data = await res.json().catch(() => null);
      setScanError(data?.detail || "Couldn't read that photo. Try again.");
      setScanLoading(false);
      return;
    }

    const data = await res.json();
    setRawText(data.raw_text);
    setResults(data.results);
    setRecipeMeta(null);
    setTitle("");
    setSaveState({ status: "idle" });
    setScanLoading(false);
  }

  async function handleSave() {
    setSaveState({ status: "saving" });

    let res: Response;
    try {
      res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/recipes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ title: title.trim() || null, raw_text: rawText }),
      });
    } catch {
      setSaveState({ status: "error", message: NETWORK_ERROR });
      return;
    }

    if (!res.ok) {
      setSaveState({ status: "error", message: "Couldn't save this recipe. Try again." });
      return;
    }

    const data = await res.json();
    setSaveState({ status: "saved", recipeId: data.recipe_id });
  }

  return (
    <main className="max-w-3xl mx-auto px-6">
      <header className="pt-14 pb-10 text-center">
        <h1 className="text-3xl font-semibold tracking-tight mb-3">
          Check a recipe for your intolerances
        </h1>
        <p className="text-muted max-w-lg mx-auto">
          Paste any recipe, look one up by name, or snap a photo of one — pick what you
          need to avoid, and get flagged ingredients with safe substitutes.
        </p>
      </header>

      {serverSlow && (
        <p
          role="status"
          className="text-sm bg-warn-soft border border-warn-border text-warn rounded-lg px-4 py-3 mb-6"
        >
          The demo server is waking up (free hosting), this can take up to a minute.
        </p>
      )}

      <section className="bg-surface border border-border rounded-2xl p-6 sm:p-8 mb-8">
        <h2 className="font-medium mb-3">
          Your restrictions
          {isLoggedIn && (
            <span className="text-xs font-normal text-muted ml-2">
              synced with your account
            </span>
          )}
        </h2>
        <div className="flex flex-wrap gap-2 mb-8">
          {tags.map((tag) => {
            const active = selectedTagIds.includes(tag.id);
            return (
              <button
                key={tag.id}
                type="button"
                onClick={() => toggleTag(tag.id)}
                className={`text-sm rounded-full px-3.5 py-1.5 border transition-colors ${
                  active
                    ? "bg-primary border-primary text-white"
                    : "border-border text-muted hover:border-primary hover:text-foreground"
                }`}
              >
                {tag.name}
              </button>
            );
          })}
        </div>

        <h2 className="font-medium mb-3">Look up a recipe by name</h2>
        <div className="flex flex-wrap gap-3 mb-2">
          <input
            type="text"
            value={lookupQuery}
            onChange={(e) => setLookupQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLookup()}
            placeholder="e.g. carbonara, chicken tikka masala..."
            className="flex-1 min-w-[200px] border border-border rounded-lg px-4 py-2.5 bg-background placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
          />
          <button
            onClick={handleLookup}
            disabled={lookupLoading}
            className="rounded-lg border border-primary text-primary px-4 py-2.5 font-medium hover:bg-primary-soft transition-colors disabled:opacity-50"
          >
            {lookupLoading ? "Looking up..." : "Look up"}
          </button>
        </div>
        {lookupError && <p className="text-sm text-danger mb-4">{lookupError}</p>}
        <p className="text-xs text-muted mb-6">
          Pulls a real original recipe from a public recipe database — well-known dishes
          only, and it fills in the text below so you can tweak it before checking.
        </p>

        <h2 className="font-medium mb-3">Or scan a recipe photo</h2>
        <div className="flex flex-wrap items-center gap-3 mb-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleScan(file);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={scanLoading}
            className="rounded-lg border border-primary text-primary px-4 py-2.5 font-medium hover:bg-primary-soft transition-colors disabled:opacity-50"
          >
            {scanLoading ? "Reading photo..." : "Take or upload a photo"}
          </button>
        </div>
        {scanError && <p className="text-sm text-danger mb-4">{scanError}</p>}
        <p className="text-xs text-muted mb-8">
          Reads text straight off a recipe card, cookbook page, or handwritten note.
          Clear, well-lit, non-cursive text works best — check the extracted text below
          before checking it.
        </p>

        <h2 className="font-medium mb-3">Recipe</h2>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          rows={8}
          placeholder={"Paste your recipe here, one ingredient per line...\ne.g.\n2 eggs\n1 cup flour\n1/2 cup milk"}
          className="w-full border border-border rounded-lg px-4 py-3 mb-5 bg-background placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
        />

        <button
          onClick={handleCheck}
          className="bg-primary text-white rounded-lg px-5 py-2.5 font-medium hover:bg-primary-hover transition-colors"
        >
          Check recipe
        </button>
        {checkError && <p className="text-sm text-danger mt-3">{checkError}</p>}
      </section>

      {results && (
        <section className="mb-16">
          {recipeMeta && (
            <div className="flex items-center gap-4 bg-surface border border-border rounded-xl p-4 mb-6">
              {recipeMeta.image_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={recipeMeta.image_url}
                  alt={recipeMeta.title}
                  className="w-16 h-16 rounded-lg object-cover shrink-0"
                />
              )}
              <div>
                <p className="font-medium">{recipeMeta.title}</p>
                {recipeMeta.source_url && (
                  <a
                    href={recipeMeta.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-primary underline"
                  >
                    Original source
                  </a>
                )}
              </div>
            </div>
          )}

          <h2 className="font-medium mb-3">Results</h2>
          <div className="space-y-3 mb-6">
            {results.map((r, i) => (
              <div
                key={i}
                className={`border rounded-xl px-4 py-3 ${
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
                  <p className="text-sm mt-1 opacity-90">
                    Conflicts with: {r.matched_tags.join(", ")}
                  </p>
                )}

                {r.substitute && (
                  <p className="text-sm mt-2 opacity-90">
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
              <p className="text-sm bg-primary-soft border border-safe-border rounded-lg px-4 py-3">
                Saved.{" "}
                <Link href={`/recipes/${saveState.recipeId}`} className="underline font-medium">
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
                  className="border border-border rounded-lg px-3 py-2 text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
                />
                <button
                  onClick={handleSave}
                  disabled={saveState.status === "saving"}
                  className="rounded-lg border border-primary text-primary px-4 py-2 text-sm font-medium hover:bg-primary-soft transition-colors disabled:opacity-50"
                >
                  {saveState.status === "saving" ? "Saving..." : "Save recipe"}
                </button>
                {saveState.status === "error" && (
                  <p className="text-sm text-danger">{saveState.message}</p>
                )}
              </div>
            )
          ) : (
            <p className="text-sm text-muted">
              <Link href="/login" className="underline text-primary">
                Log in
              </Link>{" "}
              to save this recipe and build a history.
            </p>
          )}
        </section>
      )}
    </main>
  );
}
