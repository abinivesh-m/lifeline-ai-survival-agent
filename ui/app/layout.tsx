import type { Metadata, Viewport } from "next";
import "./globals.css";
import { LocaleProvider } from "@/components/LocaleProvider";

export const metadata: Metadata = {
  title: "LIFELINE AI - Town Survival Agent",
  description:
    "A town run as a body: 100 L of diesel is blood, the hospital is the heart, the pump is the lungs. Built in Kottur, works anywhere.",
  authors: [{ name: "Abinivesh M" }],
  keywords: [
    "disaster logistics",
    "fuel allocation",
    "Kottur",
    "Tamil Nadu",
    "Meta AI",
    "agentic",
  ],
};

export const viewport: Viewport = {
  themeColor: "#060d11",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="grain antialiased">
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
