"use client";

import Link from "next/link";
import { Zap } from "lucide-react";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <header className="border-b border-line/50 bg-bg/80 backdrop-blur-md sticky top-0 z-20">
        <div className="mx-auto px-6 md:px-12 lg:px-20 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-accent/20">
              <Zap size={18} className="text-bg" />
            </div>
            <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
          </Link>
        </div>
      </header>

      <main className="flex-1 mx-auto px-6 md:px-12 lg:px-20 py-12 max-w-2xl">
        <h1 className="text-3xl font-extrabold tracking-tight mb-6">Terms of Use</h1>
        <p className="text-sm text-muted mb-4">Last updated: June 2026</p>

        <div className="prose prose-invert prose-sm max-w-none space-y-4 text-muted">
          <p>
            Welcome to WaiverEdge. By accessing or using our service, you agree to be bound by these Terms of Use.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">1. Service Description</h2>
          <p>
            WaiverEdge provides fantasy sports waiver wire recommendations and analysis tools. Our recommendations are for informational and entertainment purposes only.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">2. User Accounts</h2>
          <p>
            You are responsible for maintaining the confidentiality of your account credentials. You agree to provide accurate information when creating an account.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">3. Acceptable Use</h2>
          <p>
            You agree not to misuse the service, attempt to gain unauthorized access, or use automated means to access the service beyond normal usage patterns.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">4. Third-Party Integrations</h2>
          <p>
            WaiverEdge integrates with third-party fantasy platforms (Yahoo, ESPN). Your use of those platforms is subject to their respective terms of service.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">5. Disclaimer</h2>
          <p>
            WaiverEdge is provided &quot;as is&quot; without warranties of any kind. We do not guarantee the accuracy of recommendations or that the service will be uninterrupted.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">6. Changes</h2>
          <p>
            We may update these terms from time to time. Continued use of the service constitutes acceptance of any changes.
          </p>
        </div>

        <div className="mt-12">
          <Link href="/signin" className="text-sm text-accent hover:underline">
            ← Back to Sign In
          </Link>
        </div>
      </main>
    </div>
  );
}
