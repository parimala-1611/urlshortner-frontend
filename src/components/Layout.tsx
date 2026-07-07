import { NavLink, Outlet } from 'react-router-dom';

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition ${
    isActive
      ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
  }`;

export function Layout() {
  return (
    <div className="mx-auto flex min-h-svh w-full max-w-2xl flex-col px-4">
      <header className="flex items-center justify-between border-b border-slate-200 py-5 dark:border-slate-800">
        <span className="text-lg font-semibold tracking-tight">URL Shortener</span>
        <nav className="flex gap-2">
          <NavLink to="/" end className={navLinkClass}>
            Shorten
          </NavLink>
          <NavLink to="/stats" className={navLinkClass}>
            Stats
          </NavLink>
        </nav>
      </header>
      <main className="flex-1 py-10">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-400 dark:border-slate-800">
        No auth, no ownership — anyone with a short code can view its stats.
      </footer>
    </div>
  );
}
