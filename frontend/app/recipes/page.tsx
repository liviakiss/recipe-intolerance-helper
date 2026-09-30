"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type RecipeListItem = {
  id: number;
  title: string | null;
  created_at: string;
};

export default function RecipeHistory() {
  const [recipes, setRecipes] = useState<RecipeListItem[] | null>(null);
  const router = useRouter();

  useEffect(() => {
    async function fetchRecipes() {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/recipes`, {
        credentials: "include",
      });

      if (res.status === 401) {
        router.push("/login");
        return;
      }

      const data = await res.json();
      setRecipes(data);
    }

    fetchRecipes();
  }, [router]);

  return (
    <main className="max-w-3xl mx-auto px-6 pt-14 pb-16">
      <h1 className="text-2xl font-semibold tracking-tight mb-8">Your saved recipes</h1>

      {recipes === null && <p className="text-sm text-muted">Loading...</p>}

      {recipes && recipes.length === 0 && (
        <div className="bg-surface border border-border rounded-2xl px-6 py-10 text-center">
          <p className="text-muted mb-1">No saved recipes yet.</p>
          <Link href="/" className="text-primary underline text-sm">
            Check a recipe
          </Link>{" "}
          <span className="text-sm text-muted">and save it to see it here.</span>
        </div>
      )}

      {recipes && recipes.length > 0 && (
        <ul className="space-y-3">
          {recipes.map((recipe) => (
            <li key={recipe.id}>
              <Link
                href={`/recipes/${recipe.id}`}
                className="flex justify-between items-center bg-surface border border-border rounded-xl px-5 py-4 hover:border-primary transition-colors"
              >
                <span className="font-medium">{recipe.title || "Untitled recipe"}</span>
                <span className="text-xs text-muted">
                  {new Date(recipe.created_at).toLocaleDateString()}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
