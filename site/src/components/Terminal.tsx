export type Line = { command: string; comment?: string };

/** Install commands, set the way you'd actually see them in a shell. */
export default function Terminal({ lines }: { lines: Line[] }) {
  return (
    <div className="terminal">
      {lines.map((line) => (
        <code className="terminal__line" key={line.command}>
          <span className="terminal__prompt">$ </span>
          {line.command}
          {line.comment ? <span className="terminal__comment">{"  # " + line.comment}</span> : null}
        </code>
      ))}
    </div>
  );
}
