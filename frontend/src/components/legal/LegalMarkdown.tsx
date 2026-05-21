import React, { Fragment } from 'react';

/**
 * Lightweight markdown subset renderer for legal document content.
 *
 * Supports the subset of markdown that the BM/EN content files actually
 * use — deliberately narrow to keep this auditable and XSS-safe:
 *
 *   - Paragraphs (separated by blank lines)
 *   - Bullet lists (lines starting with "- ")
 *   - Numbered lists (lines starting with "1. ", "2. ", …)
 *   - Bold-only paragraphs are promoted to h3 sub-headings
 *   - Inline: **bold**, *italic*, `code`, [text](url)
 *
 * NEVER allows raw HTML — content is always built out of React elements,
 * never via dangerouslySetInnerHTML. If content authors need a construct
 * outside this grammar, extend the parser; don't loosen the safety model.
 *
 * Returns React elements directly — no React.createElement plumbing leaks
 * into the caller.
 */

type Block =
  | { type: 'paragraph'; text: string }
  | { type: 'h3'; text: string }
  | { type: 'bullets'; items: string[] }
  | { type: 'ordered'; items: string[]; start: number };

function parseBlocks(content: string): Block[] {
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    // Bullet list
    if (/^-\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^-\s/.test(lines[i])) {
        items.push(lines[i].replace(/^-\s/, ''));
        i++;
      }
      blocks.push({ type: 'bullets', items });
      continue;
    }

    // Numbered list
    const orderedMatch = line.match(/^(\d+)\.\s/);
    if (orderedMatch) {
      const start = parseInt(orderedMatch[1], 10);
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s/, ''));
        i++;
      }
      blocks.push({ type: 'ordered', items, start });
      continue;
    }

    // Paragraph — collect consecutive non-list, non-blank lines.
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^-\s/.test(lines[i]) &&
      !/^\d+\.\s/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    const text = paraLines.join(' ').trim();

    // Promote a paragraph that is entirely a single **bold** span to an h3
    // sub-heading — gives sub-section markers like "4.1 Pelan Tersedia"
    // proper semantic markup and visual weight.
    const wholeBold = text.match(/^\*\*([^*]+)\*\*$/);
    if (wholeBold) {
      blocks.push({ type: 'h3', text: wholeBold[1] });
    } else {
      blocks.push({ type: 'paragraph', text });
    }
  }

  return blocks;
}

// Inline grammar matched in priority order: links (most specific) → code →
// bold → italic. The link pattern requires both [text] and (url) to match,
// so it cannot collide with bracketed text used elsewhere.
const INLINE_PATTERN = /\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*/g;

function renderInline(text: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  // Fresh regex per call — global state on the shared instance would
  // leak between renders.
  const re = new RegExp(INLINE_PATTERN.source, 'g');
  let m: RegExpExecArray | null;

  while ((m = re.exec(text)) !== null) {
    if (m.index > lastIndex) {
      out.push(text.slice(lastIndex, m.index));
    }
    const [full, linkText, linkUrl, codeText, boldText, italicText] = m;

    if (linkText && linkUrl) {
      const isExternal = /^(https?:|mailto:|tel:)/.test(linkUrl);
      out.push(
        <a
          key={key++}
          href={linkUrl}
          className="text-brand-500 hover:text-brand-600 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-1 rounded-sm break-words"
          {...(isExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
        >
          {linkText}
        </a>,
      );
    } else if (codeText) {
      out.push(
        <code
          key={key++}
          className="px-1.5 py-0.5 rounded bg-ink-100 text-ink-800 text-[0.875em] font-geist-mono"
        >
          {codeText}
        </code>,
      );
    } else if (boldText) {
      out.push(
        <strong key={key++} className="font-semibold text-ink-900">
          {boldText}
        </strong>,
      );
    } else if (italicText) {
      out.push(
        <em key={key++} className="italic">
          {italicText}
        </em>,
      );
    }

    lastIndex = m.index + full.length;
  }

  if (lastIndex < text.length) {
    out.push(text.slice(lastIndex));
  }

  return out;
}

export function LegalMarkdown({ content }: { content: string }) {
  const blocks = parseBlocks(content);

  return (
    <div className="text-ink-700 leading-relaxed space-y-4">
      {blocks.map((block, idx) => {
        if (block.type === 'h3') {
          return (
            <h3
              key={idx}
              className="text-lg font-semibold text-ink-900 mt-8 mb-2 first:mt-0"
            >
              {renderInline(block.text)}
            </h3>
          );
        }
        if (block.type === 'bullets') {
          return (
            <ul key={idx} className="list-disc pl-6 space-y-2 marker:text-ink-400">
              {block.items.map((item, j) => (
                <li key={j} className="leading-relaxed">
                  {renderInline(item)}
                </li>
              ))}
            </ul>
          );
        }
        if (block.type === 'ordered') {
          return (
            <ol
              key={idx}
              start={block.start}
              className="list-decimal pl-6 space-y-2 marker:text-ink-400"
            >
              {block.items.map((item, j) => (
                <li key={j} className="leading-relaxed">
                  {renderInline(item)}
                </li>
              ))}
            </ol>
          );
        }
        return (
          <p key={idx} className="leading-relaxed">
            {renderInline(block.text)}
          </p>
        );
      })}
    </div>
  );
}
