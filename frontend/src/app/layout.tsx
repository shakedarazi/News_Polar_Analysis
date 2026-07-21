import { Heebo } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

const heebo = Heebo({
  subsets: ["hebrew", "latin"],
  variable: "--font-heebo",
});

export const metadata = {
  title: "Trust",
  description: "ניתוח פולריות בחדשות ישראל — כתבות ותגובות קהל",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="he" dir="rtl">
      <body className={`${heebo.variable} antialiased`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
