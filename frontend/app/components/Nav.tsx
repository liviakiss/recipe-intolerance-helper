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
    <nav className="flex justify-between items-center px-6 py-4 border-b">
      <Link href="/" className="font-semibold">
        Recipe Intolerance Helper
      </Link>
      <div>
        {loading ? null : email ? (
          <div className="flex items-center gap-3 text-sm">
            <span>Logged in as {email}</span>
            <Link href="/recipes" className="underline">
              History
            </Link>
            <button onClick={handleLogout} className="underline">
              Log out
            </button>
          </div>
        ) : (
          <div className="flex gap-3 text-sm">
            <Link href="/login" className="underline">
              Log in
            </Link>
            <Link href="/register" className="underline">
              Register
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
