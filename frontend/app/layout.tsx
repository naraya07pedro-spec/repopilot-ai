import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "RepoPilot AI — From issue to evidence",
  description: "Inspect a real, bounded issue-to-PR execution. Every check has an exit code.",
};
export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
