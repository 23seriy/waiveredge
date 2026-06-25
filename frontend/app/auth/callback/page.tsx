"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

function CallbackHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      localStorage.setItem("we_token", token);
    }
    router.replace("/");
  }, [searchParams, router]);

  return null;
}

export default function AuthCallbackPage() {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <Suspense fallback={<Loader2 size={24} className="animate-spin text-accent" />}>
        <CallbackHandler />
      </Suspense>
      <Loader2 size={24} className="animate-spin text-accent" />
    </div>
  );
}
