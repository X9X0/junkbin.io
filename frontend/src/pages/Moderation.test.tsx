import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../test/mocks/server';
import { render, screen, userEvent, waitFor, moderatorUser } from '../test/utils';
import Moderation from './Moderation';

const API_URL = 'http://localhost/api';
const LISTS = ['products', 'schematics', 'firmware', 'component-suggestions', 'recipes', 'product-images',
  'component-images', 'component-datasheets'];

const photo = (n: number) => ({
  id: `img-${n}`, product: 'product-1', image: `http://localhost/media/${n}.png`, caption: `Photo ${n}`,
  image_type: 'main', uploaded_by: { id: 'u1', username: 'alice' },
  uploaded_at: `2026-11-01T00:${String(n).padStart(2, '0')}:00Z`, is_approved: false,
});

describe('Moderation pending content', () => {
  let fetches: Record<string, number>;
  let images: ReturnType<typeof photo>[];

  beforeEach(() => {
    fetches = {};
    images = Array.from({ length: 25 }, (_, i) => photo(i + 1));
    server.use(
      http.get(`${API_URL}/auth/me/`, () => HttpResponse.json(moderatorUser)),
      http.get(`${API_URL}/products/pending_counts/`, () => {
        fetches.counts = (fetches.counts || 0) + 1;
        return HttpResponse.json({ products: 0, schematics: 0, firmware: 0, recipes: 0, images: images.length,
          component_images: 0, datasheets: 0, component_suggestions: 0, product_requests: 0 });
      }),
      ...LISTS.map((list) => http.get(`${API_URL}/${list}/`, () => {
        fetches[list] = (fetches[list] || 0) + 1;
        const results = list === 'product-images' ? images : [];
        return HttpResponse.json({ count: results.length, next: null, previous: null, results });
      })),
      http.post(`${API_URL}/product-images/:id/approve/`, ({ params }) => {
        images = images.filter((i) => i.id !== params.id);
        return HttpResponse.json({ detail: 'Image approved.' });
      }),
    );
    sessionStorage.clear();
  });

  it('puts an approval made by mistake back in the queue', async () => {
    let undone: unknown = null;
    server.use(http.post(`${API_URL}/product-images/:id/unapprove/`, ({ params }) => {
      undone = params.id;
      return HttpResponse.json({ detail: 'Image moved back to the queue.' });
    }));
    const user = userEvent.setup();
    render(<Moderation />);
    await screen.findByText('Photo 25');

    await user.click(screen.getAllByRole('button', { name: /^approve$/i })[0]);
    await waitFor(() => expect(screen.queryByText('Photo 25')).not.toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /recent decisions \(1\)/i }));
    await user.click(screen.getByRole('button', { name: /^undo$/i }));

    await waitFor(() => expect(undone).toBe('img-25'));
    expect(await screen.findByText('Photo 25')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /recent decisions/i })).not.toBeInTheDocument();
  }, 15000);

  it('approving refetches nothing until a list runs low', async () => {
    const user = userEvent.setup();
    render(<Moderation />);
    await screen.findByText('Photo 25');
    const before = { ...fetches };

    const approveButtons = () => screen.getAllByRole('button', { name: /^approve$/i });
    await user.click(approveButtons()[0]);
    await waitFor(() => expect(screen.queryByText('Photo 25')).not.toBeInTheDocument());
    expect(fetches).toEqual(before);
    expect(screen.getByText('24 pending items')).toBeInTheDocument();

    // down to 19 photos left: only the photo list and the counts are fetched again
    for (let n = 24; n >= 20; n--) {
      await user.click(approveButtons()[0]);
      await waitFor(() => expect(screen.queryByText(`Photo ${n}`)).not.toBeInTheDocument());
    }
    await waitFor(() => expect(fetches['product-images']).toBe(before['product-images'] + 1));
    expect(fetches.counts).toBe(before.counts + 1);
    expect(fetches.products).toBe(before.products);
  }, 15000);
});
