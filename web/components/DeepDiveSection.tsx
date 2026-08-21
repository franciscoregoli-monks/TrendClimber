"use client";

import type { ReactNode } from "react";

interface DeepDiveSectionProps {
  title: string;
  description?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export function DeepDiveSection({
  title,
  description,
  defaultOpen = false,
  children,
}: DeepDiveSectionProps) {
  return (
    <details
      className="group rounded-2xl border border-black/[0.08] bg-white"
      open={defaultOpen}
    >
      <summary className="cursor-pointer list-none px-5 py-4 marker:content-none [&::-webkit-details-marker]:hidden">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[var(--hack-text)]">{title}</p>
            {description && (
              <p className="mt-1 text-xs text-[var(--hack-text-muted)]">{description}</p>
            )}
          </div>
          <span className="text-xs font-medium text-[var(--hack-purple)] group-open:hidden">
            Expand
          </span>
          <span className="hidden text-xs font-medium text-[var(--hack-purple)] group-open:inline">
            Collapse
          </span>
        </div>
      </summary>
      <div className="border-t border-black/[0.06] px-5 py-4">{children}</div>
    </details>
  );
}
