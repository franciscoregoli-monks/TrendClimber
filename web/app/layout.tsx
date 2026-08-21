import type { Metadata } from "next";
import "./globals.css";

import { BackgroundVideo } from "@/components/BackgroundVideo";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "TrendClimber | Monks AI Hackathon",
  description:
    "Detecta en qué fase está una tendencia antes de que se masifique — keywords con IA + Google Trends",
  icons: {
    icon: "/trendclimber-logo.png",
    apple: "/trendclimber-logo.png",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" className="h-full">
      <body className="min-h-full antialiased">
        <BackgroundVideo />
        <Navbar />
        <main className="relative">{children}</main>
      </body>
    </html>
  );
}
