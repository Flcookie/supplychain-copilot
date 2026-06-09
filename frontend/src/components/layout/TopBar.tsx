export function TopBar() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold text-[#1e3a5f]">ProcureAI</span>
        <span className="text-sm text-slate-500">Ratti SpA · Supplier Management</span>
      </div>
      <div className="text-sm text-slate-700">Sarah Chen (Buyer)</div>
    </header>
  );
}
