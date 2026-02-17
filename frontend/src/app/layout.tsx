import type { Metadata } from 'next';
import { Manrope, Space_Grotesk } from 'next/font/google';

import './globals.css';
import Navbar from '@/components/Navbar';

const manrope = Manrope({ subsets: ['latin'], variable: '--font-manrope' });
const space = Space_Grotesk({ subsets: ['latin'], variable: '--font-space' });

export const metadata: Metadata = {
  title: 'SonataOps Studio',
  description: 'Enterprise ops intelligence with sonification and grounded RAG copilot'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${space.variable} font-[var(--font-manrope)]`}>
        <Navbar />
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
