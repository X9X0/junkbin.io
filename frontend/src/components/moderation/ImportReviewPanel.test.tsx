import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { render, screen, userEvent } from '../../test/utils';
import ImportReviewPanel, { isCompleted } from './ImportReviewPanel';

const API_URL = 'http://localhost/api';
const batch = (o: Partial<Record<string, unknown>>) => ({
  batch: 'x', label: 'X', item_type: 'product', total: 10, reviewed: 0, correct: 0, flagged: 0, target: 10, unapproved: 10, can_approve: false, ...o,
});

describe('ImportReviewPanel', () => {
  beforeEach(() => {
    server.use(http.get(`${API_URL}/import-review/`, () => HttpResponse.json([
      batch({ batch: 'open', label: 'Boards still to review', unapproved: 4 }),
      batch({ batch: 'flagged', label: 'Published but flagged', unapproved: 0, flagged: 1, reviewed: 3, correct: 2 }),
      batch({ batch: 'done', label: 'Chip pictures', unapproved: 0, reviewed: 10, correct: 10 }),
      batch({ batch: 'done2', label: 'Teardowns', unapproved: 0, reviewed: 2, correct: 2 }),
    ])));
  });

  it('is completed only with nothing left to publish and no open flag', () => {
    expect(isCompleted(batch({ unapproved: 0, flagged: 0 }))).toBe(true);
    expect(isCompleted(batch({ unapproved: 0, flagged: 1 }))).toBe(false);
    expect(isCompleted(batch({ unapproved: 3, flagged: 0 }))).toBe(false);
  });

  it('collapses the completed batches under a Completed section at the bottom', async () => {
    render(<ImportReviewPanel />);
    const toggle = await screen.findByRole('button', { name: /Completed \(2\)/ });
    expect(screen.getByText('Boards still to review')).toBeInTheDocument();
    expect(screen.getByText('Published but flagged')).toBeInTheDocument();
    expect(screen.queryByText('Chip pictures')).not.toBeInTheDocument();
    expect(toggle.compareDocumentPosition(screen.getByText('Published but flagged')) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
    await userEvent.click(toggle);
    expect(screen.getByText('Chip pictures')).toBeInTheDocument();
    expect(screen.getByText('Teardowns')).toBeInTheDocument();
    await userEvent.click(toggle);
    expect(screen.queryByText('Chip pictures')).not.toBeInTheDocument();
  });
});
