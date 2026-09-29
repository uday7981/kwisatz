import type { Metadata } from "next";
import { Bricolage_Grotesque, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/components/query-provider";
import { NavRail } from "@/components/nav-rail";
import { TopBar } from "@/components/top-bar";

const display = Bricolage_Grotesque({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600"],
});

const body = IBM_Plex_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Underdog",
  description: "The prospecting agent that learns which Amazon brands say yes.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} bg-surface text-ink`}>
        <QueryProvider>
          <div className="min-h-screen flex">
            <NavRail />
            <main className="flex-1 flex flex-col min-w-0">
              <TopBar />
              <div className="flex-1 px-8 py-10 max-w-[1100px] mx-auto w-full">
                {children}
              </div>
            </main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
