"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function Nav() {
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function fetchUser() {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/me`, {
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        setEmail(data.email);
      }
      setLoading(false);
    }

    fetchUser();
  }, []);

  async function handleLogout() {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/logout`, {
      method: "POST",
      credentials: "include",
    });
    setEmail(null);
    router.refresh();
  }

  return (
    <nav className="sticky top-0 z-10 bg-surface/90 backdrop-blur border-b border-border">
      <div className="max-w-3xl mx-auto flex justify-between items-center px-6 py-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            className="text-primary"
          >
            <path
              d="M4 13c0-5 4-9 9-9 3.5 0 3.5 3.5 3.5 3.5S13 7 13 10.5 16.5 14 16.5 14 20 14 20 17.5c0 0-4.5 3.5-9.5 3.5-4.5 0-6.5-3.5-6.5-8Z"
              fill="currentColor"
            />
          </svg>
          Recipe Intolerance Helper
        </Link>

        <div>
          {loading ? null : email ? (
            <div className="flex items-center gap-4 text-sm">
              <span className="text-muted hidden sm:inline">
                Logged in as <span className="text-foreground">{email}</span>
              </span>
              <Link
                href="/recipes"
                className="rounded-full border border-border px-3 py-1.5 hover:bg-primary-soft hover:border-primary transition-colors"
              >
                History
              </Link>
              <button
                onClick={handleLogout}
                className="text-muted hover:text-foreground transition-colors"
              >
                Log out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-sm">
              <Link href="/login" className="text-muted hover:text-foreground transition-colors">
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded-full bg-primary text-white px-3.5 py-1.5 hover:bg-primary-hover transition-colors"
              >
                Register
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
