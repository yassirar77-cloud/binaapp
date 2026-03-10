'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

interface InlineEditorProps {
  html: string;
  onHtmlChange: (newHtml: string) => void;
}

export default function InlineEditor({ html, onHtmlChange }: InlineEditorProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');
  const [editingTag, setEditingTag] = useState('');
  const [showEditModal, setShowEditModal] = useState(false);
  const [editPath, setEditPath] = useState<number[]>([]);

  // Build a CSS path index to locate elements in the HTML string
  function getElementPath(element: Element, root: Element): number[] {
    const path: number[] = [];
    let current: Element | null = element;
    while (current && current !== root) {
      const parent = current.parentElement;
      if (!parent) break;
      const index = Array.from(parent.children).indexOf(current);
      path.unshift(index);
      current = parent;
    }
    return path;
  }

  const injectEditingScript = useCallback(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const doc = iframe.contentDocument;
    if (!doc) return;

    // Inject hover/click styles and handlers
    const style = doc.createElement('style');
    style.textContent = `
      [data-bina-hover] {
        outline: 2px dashed #3b82f6 !important;
        outline-offset: 2px !important;
        cursor: pointer !important;
      }
      [data-bina-selected] {
        outline: 2px solid #3b82f6 !important;
        outline-offset: 2px !important;
        background-color: rgba(59, 130, 246, 0.05) !important;
      }
    `;
    doc.head.appendChild(style);

    // Add event listeners to all editable elements
    const editableSelectors = 'h1,h2,h3,h4,h5,h6,p,span,a,li,td,th,button,label,figcaption,blockquote,dt,dd,caption';

    doc.body.addEventListener('mouseover', (e) => {
      const target = (e.target as Element).closest(editableSelectors);
      if (target) {
        target.setAttribute('data-bina-hover', 'true');
      }
    });

    doc.body.addEventListener('mouseout', (e) => {
      const target = (e.target as Element).closest(editableSelectors);
      if (target) {
        target.removeAttribute('data-bina-hover');
      }
    });

    doc.body.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();

      const target = (e.target as Element).closest(editableSelectors);
      if (!target) return;

      // Remove previous selection
      doc.querySelectorAll('[data-bina-selected]').forEach(el =>
        el.removeAttribute('data-bina-selected')
      );

      target.setAttribute('data-bina-selected', 'true');

      const path = getElementPath(target, doc.body);
      const text = target.textContent || '';
      const tag = target.tagName.toLowerCase();

      // Post message to parent
      window.postMessage({
        type: 'bina-inline-edit',
        text,
        tag,
        path,
      }, '*');
    }, true);
  }, []);

  // Listen for messages from the iframe
  useEffect(() => {
    function handleMessage(e: MessageEvent) {
      if (e.data?.type === 'bina-inline-edit') {
        setEditingText(e.data.text);
        setEditingTag(e.data.tag);
        setEditPath(e.data.path);
        setSelectedElement(e.data.tag);
        setShowEditModal(true);
      }
    }
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // When iframe loads, inject the editing scripts
  const handleIframeLoad = useCallback(() => {
    // Small delay to ensure DOM is ready
    setTimeout(() => injectEditingScript(), 100);
  }, [injectEditingScript]);

  function applyEdit() {
    // Parse the HTML, navigate to the element by path, and update its text
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    let element: Element | null = doc.body;
    for (const index of editPath) {
      if (!element) break;
      element = element.children[index] || null;
    }

    if (element) {
      element.textContent = editingText;

      // Serialize back to full HTML
      // Preserve the original doctype and structure
      const serializer = new XMLSerializer();
      let newHtml: string;

      if (html.toLowerCase().includes('<!doctype') || html.toLowerCase().includes('<html')) {
        // Full HTML document - reconstruct with doctype
        newHtml = '<!DOCTYPE html>\n' + doc.documentElement.outerHTML;
      } else {
        // Partial HTML - just return body contents
        newHtml = doc.body.innerHTML;
      }

      onHtmlChange(newHtml);
    }

    setShowEditModal(false);
    setSelectedElement(null);
  }

  function getTagLabel(tag: string): string {
    const labels: Record<string, string> = {
      h1: 'Tajuk Utama (H1)',
      h2: 'Tajuk (H2)',
      h3: 'Sub-tajuk (H3)',
      h4: 'Sub-tajuk (H4)',
      h5: 'Sub-tajuk (H5)',
      h6: 'Sub-tajuk (H6)',
      p: 'Perenggan',
      span: 'Teks',
      a: 'Pautan',
      li: 'Item Senarai',
      button: 'Butang',
      label: 'Label',
      td: 'Sel Jadual',
      th: 'Pengepala Jadual',
      figcaption: 'Kapsyen',
      blockquote: 'Petikan',
    };
    return labels[tag] || tag.toUpperCase();
  }

  return (
    <div className="flex-1 flex flex-col relative">
      {/* Instruction bar */}
      <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 flex items-center gap-2">
        <span className="text-blue-600 text-lg">&#9432;</span>
        <p className="text-sm text-blue-700">
          Klik pada mana-mana teks dalam preview untuk edit terus. Tiada kod HTML diperlukan!
        </p>
      </div>

      {/* Full-width preview iframe with click-to-edit */}
      <div className="flex-1 bg-white">
        <iframe
          ref={iframeRef}
          srcDoc={html}
          className="w-full h-full border-0"
          title="Inline Editor Preview"
          sandbox="allow-scripts allow-same-origin allow-forms"
          onLoad={handleIframeLoad}
        />
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="bg-blue-500 text-white px-6 py-4">
              <h3 className="font-bold text-lg">Edit {getTagLabel(editingTag)}</h3>
              <p className="text-blue-100 text-sm mt-1">Tukar teks di bawah dan tekan Simpan</p>
            </div>
            <div className="p-6">
              {editingTag === 'p' || editingTag === 'blockquote' || editingTag === 'li' ? (
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  rows={4}
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                  autoFocus
                />
              ) : (
                <input
                  type="text"
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && applyEdit()}
                />
              )}
            </div>
            <div className="bg-gray-50 px-6 py-4 flex gap-3 justify-end">
              <button
                onClick={() => { setShowEditModal(false); setSelectedElement(null); }}
                className="px-5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
              >
                Batal
              </button>
              <button
                onClick={applyEdit}
                className="px-5 py-2.5 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors"
              >
                Simpan Perubahan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
