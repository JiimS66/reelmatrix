export function LoadingState() {
  return (
    <div
      role="status"
      className="panel flex items-center gap-4 border-moss/20 bg-emerald-50/70"
    >
      <span className="h-9 w-9 animate-spin rounded-full border-4 border-moss/20 border-t-moss" />
      <div>
        <p className="font-semibold text-ink">Building campaign strategy</p>
        <p className="mt-1 text-sm text-slate-600">
          The ideation and planning workflow is processing your brief.
        </p>
      </div>
    </div>
  );
}
