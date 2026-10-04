import type { Metadata, Viewport } from "next";
import "./globals.css";

const NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? "GB Renewable Energy Atlas";
export const metadata: Metadata = {
  title: { default: NAME, template: `%s · ${NAME}` },
  description: "Renewable generation, storage, planning and grid intelligence across Great Britain – every figure traceable to its source.",
};
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

const themeInit = `try{var t=localStorage.getItem('atlas.theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t)}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeInit }} /></head>
      <body>
        <a className="skip" href="#main">Skip to main content</a>
        {children}
      </body>
    </html>
  );
}
