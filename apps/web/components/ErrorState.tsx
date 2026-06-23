export function ErrorState({ message }: { message: string }) {
  return (
    <div role="alert" className="panel border-red-200 bg-red-50/80">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-red-700">
        Request failed
      </p>
      <p className="mt-2 font-semibold text-red-950">{message}</p>
      <p className="mt-2 text-sm text-red-800">
        Review the backend configuration and your campaign brief, then submit again.
      </p>
    </div>
  );
}
