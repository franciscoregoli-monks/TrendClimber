import Link from "next/link";

import { TrendClimberLogo } from "./TrendClimberLogo";

export function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-white/20 bg-white/55 px-6 backdrop-blur-2xl backdrop-saturate-150">
      <div className="mx-auto flex h-[58px] max-w-[1160px] items-center justify-between">
        <Link
          href="/"
          className="flex items-center no-underline opacity-90 transition-opacity hover:opacity-100"
        >
          <TrendClimberLogo />
        </Link>

        <span className="text-[13px] font-medium tracking-[-0.02em] text-[var(--hack-text-muted)]">
          Monks AI Hackathon
        </span>
      </div>
    </nav>
  );
}
