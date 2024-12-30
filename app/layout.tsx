'use client';

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { ThemeProvider } from '@/components/theme-provider';
import { FilePathContext } from '@/components/file-upload';
import { useState } from 'react';

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [filePath, setFilePath] = useState<string | null>(null);

  return (
    <html lang="zh">
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <FilePathContext.Provider value={{ filePath, setFilePath }}>
            {children}
            <Toaster />
          </FilePathContext.Provider>
        </ThemeProvider>
      </body>
    </html>
  );
}