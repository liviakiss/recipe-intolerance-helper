"use client";

import { useState } from "react";
import Link from "next/link";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      setError(data.detail || "Something went wrong");
      return;
    }

    // A full reload (not router.push) so Nav and the home page remount
    // and re-fetch /me and /me/restrictions with the cookie already set.
    window.location.href = "/";
  }

  return (
    <div className="max-w-sm mx-auto mt-20 px-6">
      <div className="bg-surface border border-border rounded-2xl p-8">
        <h1 className="text-xl font-semibold mb-6">Log in</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="border border-border rounded-lg px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="border border-border rounded-lg px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
          />
          {error && <p className="text-danger text-sm">{error}</p>}
          <button
            type="submit"
            className="bg-primary text-white rounded-lg px-3 py-2.5 font-medium hover:bg-primary-hover transition-colors"
          >
            Log in
          </button>
        </form>
        <p className="text-sm text-muted mt-5 text-center">
          No account yet?{" "}
          <Link href="/register" className="text-primary underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
