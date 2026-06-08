export default function Spinner({
  label = "Loading...",
  size = "md",
}: {
  label?: string;
  size?: "sm" | "md" | "lg";
}) {
  const ring: Record<string, string> = {
    sm: "w-5 h-5 border-2",
    md: "w-8 h-8 border-4",
    lg: "w-12 h-12 border-4",
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <div
        className={`${ring[size]} border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin`}
      />
      {label && (
        <p className="font-mono text-cyan-400 text-xs uppercase tracking-widest animate-pulse">
          {label}
        </p>
      )}
    </div>
  );
}
