export interface LegalSourceRef {
  id: string;
  label: string;
  source_url: string;
  law?: string;
}

const CITATION_MARKER = /(\[LAW_\d+\])/g;

export default function CitedText({
  text,
  sources,
}: {
  /** Old archived matches can have an omitted verdict/turn text. */
  text?: string | null;
  sources?: LegalSourceRef[] | null;
}) {
  const safeText = typeof text === "string" ? text : "";
  const sourcesById = new Map((sources ?? []).map((source) => [source.id, source]));

  return (
    <span className="whitespace-pre-wrap">
      {safeText.split(CITATION_MARKER).map((part, index) => {
        const markerMatch = /^\[(LAW_\d+)\]$/.exec(part);
        const source = markerMatch ? sourcesById.get(markerMatch[1]) : undefined;
        if (!source) {
          return <span key={`${part}-${index}`}>{part}</span>;
        }
        return (
          <a
            key={`${source.id}-${index}`}
            href={source.source_url}
            target="_blank"
            rel="noreferrer"
            title={source.label}
            className="font-semibold underline decoration-dotted underline-offset-2 hover:opacity-75"
          >
            {source.label}
          </a>
        );
      })}
    </span>
  );
}
