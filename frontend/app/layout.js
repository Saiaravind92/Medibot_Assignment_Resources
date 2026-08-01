import './globals.css'

export const metadata = {
  title: 'MediBot — Advanced RAG Console',
  description: 'Role-Based Access Control and Hybrid RAG System',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-950 text-slate-100">{children}</body>
    </html>
  )
}
