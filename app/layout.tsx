import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bengaluru Demand Command Center",
  description: "Real-time zone-level ride demand prediction demo",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
