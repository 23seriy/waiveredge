"use client";

import Link from "next/link";
import { Zap } from "lucide-react";

export default function PrivacyPage() {
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
        <h1 className="text-3xl font-extrabold tracking-tight mb-6">Privacy Policy</h1>
        <p className="text-sm text-muted mb-4">Last updated: June 2026</p>

        <div className="prose prose-invert prose-sm max-w-none space-y-4 text-muted">
          <p>
            Your privacy is important to us. This Privacy Policy explains how WaiverEdge collects, uses, and protects your information.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">1. Information We Collect</h2>
          <p>
            We collect information you provide directly: email address, name, and fantasy league data when you connect your accounts. We also collect usage data to improve the service.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">2. How We Use Your Information</h2>
          <p>
            We use your information to provide personalized waiver recommendations, manage your account, and improve our service. We do not sell your personal information.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">3. Third-Party Services</h2>
          <p>
            We integrate with Yahoo and ESPN to access your fantasy league data. We only access the league and roster information necessary to provide recommendations.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">4. Data Security</h2>
          <p>
            We use industry-standard security measures to protect your data, including encrypted connections and secure token storage. Passwords are hashed and never stored in plain text.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">5. Data Retention</h2>
          <p>
            We retain your account data as long as your account is active. You may request deletion of your account and associated data at any time by contacting us.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">6. Changes</h2>
          <p>
            We may update this Privacy Policy from time to time. We will notify you of any significant changes through the service.
          </p>

          <h2 className="text-lg font-bold text-foreground mt-8 mb-3">7. Contact</h2>
          <p>
            If you have questions about this Privacy Policy, please reach out through our support channels.
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
