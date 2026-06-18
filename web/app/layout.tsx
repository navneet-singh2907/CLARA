import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CLARA | Credit Loan Analysis & Review Agent",
  description: "LangGraph multi-agent small business loan review product"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
