import type { Metadata } from "next";
import { headers } from "next/headers";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Pustak - AI-Powered Documentation Platform",
    template: "%s | Pustak"
  },
  description: "Beautiful, AI-powered documentation platform that automatically generates and maintains documentation for your repositories. Powered by DocAI.",
  keywords: ["documentation", "docs", "gitbook", "ai", "markdown", "github", "automatic documentation", "code documentation"],
  authors: [{ name: "Pustak Team" }],
  creator: "Pustak",
  publisher: "Pustak",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://pustak.dev',
    title: 'Pustak - AI-Powered Documentation Platform',
    description: 'Beautiful, AI-powered documentation platform that automatically generates and maintains documentation for your repositories.',
    siteName: 'Pustak',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Pustak - AI-Powered Documentation Platform',
    description: 'Beautiful, AI-powered documentation platform that automatically generates and maintains documentation for your repositories.',
    creator: '@pustak',
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const headersList = await headers();
  const hostHeader = headersList.get("host")?.toLowerCase() || "";
  const normalizedHost = hostHeader.replace(/:\d+$/, "");
  const docbookSuffix = (
    process.env.NEXT_PUBLIC_DOCBOOK_DOMAIN || "docbook.site"
  )
    .toLowerCase()
    .replace(/^\.+/, "");
  const isDocbookHost = Boolean(
    docbookSuffix &&
      (normalizedHost === docbookSuffix ||
        normalizedHost.endsWith(`.${docbookSuffix}`))
  );

  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers isDocbookHost={isDocbookHost}>{children}</Providers>
      </body>
    </html>
  );
}
