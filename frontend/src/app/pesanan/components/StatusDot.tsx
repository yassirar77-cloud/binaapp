'use client';

/** Solid colored dot — used by OrderCard to indicate status at a glance.
 *  Color comes from STATUS_META in constants.ts. Kept dumb on purpose so
 *  parents stay in control of which color maps to which status. */

interface Props {
  color: string;
  size?: number;
  className?: string;
}

export default function StatusDot({ color, size = 10, className = '' }: Props) {
  return (
    <span
      aria-hidden
      className={`inline-block shrink-0 rounded-full ${className}`}
      style={{
        width: size,
        height: size,
        backgroundColor: color,
        boxShadow: `0 0 0 3px ${color}1f`,
      }}
    />
  );
}
