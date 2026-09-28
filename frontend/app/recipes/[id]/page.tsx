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
      <main className="max-w-2xl mx-auto mt-12 px-6">
        <p className="text-sm text-gray-500">
          That recipe doesn&apos;t exist, or isn&apos;t yours.{" "}
          <Link href="/recipes" className="underline">
            Back to history
          </Link>
        </p>
      </main>
    );
  }

  if (!recipe) {
    return (
      <main className="max-w-2xl mx-auto mt-12 px-6">
        <p className="text-sm text-gray-500">Loading...</p>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto mt-12 px-6">
      <Link href="/recipes" className="text-sm underline">
        Back to history
      </Link>

      <h1 className="text-2xl font-semibold mt-2 mb-1">
        {recipe.title || "Untitled recipe"}
      </h1>
      <p className="text-xs text-gray-500 mb-6">
        Saved {new Date(recipe.created_at).toLocaleString()}
      </p>

      <h2 className="font-medium mb-2">Recipe</h2>
      <pre className="text-sm bg-gray-100 text-gray-900 p-4 rounded overflow-auto whitespace-pre-wrap mb-6">
        {recipe.raw_text}
      </pre>

      <h2 className="font-medium mb-2">Flagged ingredients</h2>
      {recipe.results.length === 0 ? (
        <p className="text-sm text-gray-500">
          Nothing was flagged for this recipe.
        </p>
      ) : (
        <div className="space-y-3">
          {recipe.results.map((r, i) => (
            <div
              key={i}
              className="border rounded px-4 py-3 bg-red-50 border-red-300 text-red-900"
            >
              <p className="font-medium">{r.ingredient_name}</p>
              <p className="text-sm mt-1">Conflicts with: {r.flagged_tag_name}</p>
              {r.substitute_name && (
                <p className="text-sm mt-2">
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
