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
    <main className="max-w-2xl mx-auto mt-12 px-6">
      <h1 className="text-2xl font-semibold mb-6">Your saved recipes</h1>

      {recipes === null && <p className="text-sm text-gray-500">Loading...</p>}

      {recipes && recipes.length === 0 && (
        <p className="text-sm text-gray-500">
          No saved recipes yet.{" "}
          <Link href="/" className="underline">
            Check one
          </Link>{" "}
          and save it to see it here.
        </p>
      )}

      {recipes && recipes.length > 0 && (
        <ul className="space-y-2">
          {recipes.map((recipe) => (
            <li key={recipe.id}>
              <Link
                href={`/recipes/${recipe.id}`}
                className="flex justify-between items-center border rounded px-4 py-3 bg-white text-gray-900 hover:bg-gray-50"
              >
                <span>{recipe.title || "Untitled recipe"}</span>
                <span className="text-xs text-gray-500">
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
