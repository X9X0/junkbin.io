import { useEffect, useRef, useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import * as pdfjs from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

/**
 * A PDF drawn page by page onto canvases with pdf.js. Phone browsers (Android Chrome above all,
 * and the installed PWA) have no built-in PDF viewer, so an <iframe> of a PDF shows nothing there.
 * Pages are drawn as they scroll into view, so a 100-page manual doesn't render all at once.
 */
export default function PdfPages({ url, className = 'h-[65vh]' }: { url: string; className?: string }) {
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const task = pdfjs.getDocument({ url, isEvalSupported: false });
    task.promise.then((d) => { if (!cancelled) setDoc(d); }, () => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; task.destroy(); };
  }, [url]);

  if (failed) {
    return (
      <a href={url} download className="inline-flex items-center gap-2 text-sm text-cyber-cyan hover:underline">
        <Download className="h-4 w-4" /> Could not show this PDF here: download it
      </a>
    );
  }
  if (!doc) {
    return <div className={`${className} flex items-center justify-center text-gray-500 text-sm`}><Loader2 className="h-4 w-4 animate-spin mr-2" />Loading document…</div>;
  }
  return (
    <div className={`${className} overflow-y-auto bg-gray-800 border border-cyber-light/20 p-1 space-y-1`}>
      <div className="text-xs text-gray-400 px-1">{doc.numPages} page{doc.numPages === 1 ? '' : 's'}</div>
      {Array.from({ length: doc.numPages }, (_, i) => <PdfPage key={i} doc={doc} number={i + 1} />)}
    </div>
  );
}

function PdfPage({ doc, number }: { doc: PDFDocumentProxy; number: number }) {
  const holder = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [visible, setVisible] = useState(number === 1);
  const [drawn, setDrawn] = useState(false);

  useEffect(() => {
    if (visible || !holder.current) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true); }, { rootMargin: '600px' });
    io.observe(holder.current);
    return () => io.disconnect();
  }, [visible]);

  useEffect(() => {
    if (!visible || drawn || !canvas.current || !holder.current) return;
    let cancelled = false;
    let renderTask: { cancel: () => void } | null = null;
    doc.getPage(number).then((page) => {
      if (cancelled || !canvas.current || !holder.current) return;
      const width = holder.current.clientWidth || 600;
      const base = page.getViewport({ scale: 1 });
      const ratio = window.devicePixelRatio || 1;
      const viewport = page.getViewport({ scale: (width / base.width) * ratio });
      const c = canvas.current;
      c.width = viewport.width;
      c.height = viewport.height;
      c.style.width = '100%';
      const task = page.render({ canvasContext: c.getContext('2d')!, viewport });
      renderTask = task;
      task.promise.then(() => { if (!cancelled) setDrawn(true); }, () => {});
    });
    return () => { cancelled = true; renderTask?.cancel(); };
  }, [visible, drawn, doc, number]);

  return (
    <div ref={holder} className="bg-white min-h-[200px]">
      <canvas ref={canvas} className="block w-full" aria-label={`Page ${number}`} />
    </div>
  );
}
