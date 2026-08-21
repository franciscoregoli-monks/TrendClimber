import Image from "next/image";

interface TrendClimberLogoProps {
  showWordmark?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE_CONFIG = {
  sm: { icon: 34, wordmark: "text-[20px] font-semibold tracking-[-0.025em]" },
  md: { icon: 44, wordmark: "text-[32px] font-semibold tracking-[-0.035em]" },
  lg: {
    icon: 56,
    wordmark:
      "text-[max(40px,min(5.5vw,64px))] font-semibold leading-[1.05] tracking-[-0.045em]",
  },
} as const;

export function TrendClimberLogo({
  showWordmark = true,
  size = "sm",
  className = "",
}: TrendClimberLogoProps) {
  const config = SIZE_CONFIG[size];

  return (
    <span className={`inline-flex items-center gap-3 ${className}`}>
      <Image
        src="/trendclimber-logo.png"
        alt=""
        width={config.icon}
        height={config.icon}
        className="shrink-0"
        priority
      />
      {showWordmark && (
        <span className={`${config.wordmark} text-[var(--hack-text)]`}>
          Trend
          <span className={size === "lg" ? "hack-title-accent" : "text-[var(--hack-purple)]"}>
            Climber
          </span>
        </span>
      )}
    </span>
  );
}
