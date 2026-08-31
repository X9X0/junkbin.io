import type { ReactNode } from 'react';

const URL_PATTERN = /(https?:\/\/[^\s)]+)/g;

/**
 * Splits plain text on http(s) URLs and renders them as real links.
 * Trailing punctuation commonly adjacent to a URL in prose (periods,
 * closing parens/commas) is kept out of the href so links don't 404.
 *
 * Uses String.split with a capturing group: the result alternates
 * plain-text / matched-URL / plain-text / ..., so odd indices are always
 * URLs — this avoids re-testing with a stateful global regex.
 */
export function linkify(text: string): ReactNode[] {
  const parts = text.split(URL_PATTERN);
  return parts.map((part, i) => {
    if (i % 2 === 0) {
      return part;
    }

    const trailingMatch = part.match(/[).,;:]+$/);
    const trailing = trailingMatch ? trailingMatch[0] : '';
    const href = trailing ? part.slice(0, -trailing.length) : part;

    return (
      <span key={i}>
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyber-cyan hover:underline break-all"
        >
          {href}
        </a>
        {trailing}
      </span>
    );
  });
}
