import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { mockProduct } from '../../test/mocks/handlers';
import { render, screen, userEvent, waitFor } from '../../test/utils';
import ReviewViewer from './ReviewViewer';
import type { PendingItem } from './pendingItems';

const API_URL = 'http://localhost/api';

const photo = (id: string, caption: string): PendingItem => ({
  type: 'image',
  data: {
    id, product: 'product-1', image: `http://localhost/media/${id}.png`, caption, image_type: 'main',
    uploaded_by: { id: 'u1', username: 'alice' }, uploaded_at: '2026-11-01T00:00:00Z', is_approved: false,
  },
});

const items = [photo('img-1', 'Front'), photo('img-2', 'Back')];

describe('ReviewViewer', () => {
  beforeEach(() => {
    localStorage.clear();
    server.use(http.get(`${API_URL}/products/:id/`, () => HttpResponse.json(mockProduct)));
  });

  it('sends the rejection feedback and moves on to the next item', async () => {
    let body: unknown = null;
    server.use(http.post(`${API_URL}/product-images/img-1/reject/`, async ({ request }) => {
      body = await request.json();
      return new HttpResponse(null, { status: 204 });
    }));
    const onDecided = vi.fn();
    const onNavigate = vi.fn();
    const user = userEvent.setup();
    render(<ReviewViewer items={items} activeKey="image-img-1" onNavigate={onNavigate} onClose={vi.fn()} onDecided={onDecided} />);

    expect(screen.getByText('1 / 2')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /reject…/i }));
    expect(screen.getByText(/feedback to/i)).toHaveTextContent('alice');
    await user.click(screen.getByRole('button', { name: 'Different product' }));
    await user.click(screen.getByRole('button', { name: /reject and send feedback/i }));

    await waitFor(() => expect(onDecided).toHaveBeenCalledWith('image-img-1'));
    expect(body).toEqual({ notes: 'The photo shows a different product or model.' });
    expect(onNavigate).toHaveBeenCalledWith('image-img-2');
  });

  it('closes after a decision when "continue" is unticked', async () => {
    server.use(http.post(`${API_URL}/product-images/img-2/approve/`, () => HttpResponse.json({ detail: 'Image approved.' })));
    const onClose = vi.fn();
    const onNavigate = vi.fn();
    const user = userEvent.setup();
    render(<ReviewViewer items={items} activeKey="image-img-2" onNavigate={onNavigate} onClose={onClose} onDecided={vi.fn()} />);

    await user.click(screen.getByRole('checkbox', { name: /continue to next item/i }));
    await user.click(screen.getByRole('button', { name: /approve/i }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(onNavigate).not.toHaveBeenCalled();
    expect(localStorage.getItem('moderation.continueNext')).toBe('false');
  });
});
