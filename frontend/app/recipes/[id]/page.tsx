"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

type RecipeResultItem = {
  ingredient_name: string;
  flagged_tag_name: string;
  substitute_name: string | null;
  substitute_note: string | null;
};

type RecipeDetail = {
  id: number;
  title: string | null;
  raw_text: string;
  created_at: string;
  results: RecipeResultItem[];
};

export default function RecipeDetailPage() {
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const params = useParams();
  const router = useRouter();

  useEffect(() => {
    async function fetchRecipe() {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/recipes/${params.id}`,
        { credentials: "include" }
      );

      if (res.status === 401) {
        router.push("/login");
        return;
      }

      if (res.status === 404) {
        setNotFound(true);
        return;
      }

      const data = await res.json();
      setRecipe(data);
    }

    fetchRecipe();
  }, [params.id, router]);

  if (notFound) {
    return (
      <main className="max-w-3xl mx-auto px-6 pt-14">
        <div className="bg-surface border border-border rounded-2xl px-6 py-10 text-center">
          <p className="text-muted mb-1">
            That recipe doesn&apos;t exist, or isn&apos;t yours.
          </p>
          <Link href="/recipes" className="text-primary underline text-sm">
            Back to history
          </Link>
        </div>
      </main>
    );
  }

  if (!recipe) {
    return (
      <main className="max-w-3xl mx-auto px-6 pt-14">
        <p className="text-sm text-muted">Loading...</p>
      </main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto px-6 pt-14 pb-16">
      <Link href="/recipes" className="text-sm text-primary underline">
        Back to history
      </Link>

      <h1 className="text-2xl font-semibold tracking-tight mt-3 mb-1">
        {recipe.title || "Untitled recipe"}
      </h1>
      <p className="text-xs text-muted mb-8">
        Saved {new Date(recipe.created_at).toLocaleString()}
      </p>

      <section className="bg-surface border border-border rounded-2xl p-6 mb-8">
        <h2 className="font-medium mb-3">Recipe</h2>
        <pre className="text-sm bg-background border border-border text-foreground p-4 rounded-lg overflow-auto whitespace-pre-wrap">
          {recipe.raw_text}
        </pre>
      </section>

      <h2 className="font-medium mb-3">Flagged ingredients</h2>
      {recipe.results.length === 0 ? (
        <p className="text-sm text-muted">Nothing was flagged for this recipe.</p>
      ) : (
        <div className="space-y-3">
          {recipe.results.map((r, i) => (
            <div
              key={i}
              className="border rounded-xl px-4 py-3 bg-danger-soft border-danger-border text-danger"
            >
              <p className="font-medium">{r.ingredient_name}</p>
              <p className="text-sm mt-1 opacity-90">
                Conflicts with: {r.flagged_tag_name}
              </p>
              {r.substitute_name && (
                <p className="text-sm mt-2 opacity-90">
                  Try instead:{" "}
                  <span className="font-medium">{r.substitute_name}</span>
                  {r.substitute_note && ` — ${r.substitute_note}`}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
