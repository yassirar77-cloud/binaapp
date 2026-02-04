'use client';
import { useState } from 'react';

interface AIEditorProps {
  html: string;
  onHtmlChange: (newHtml: string) => void;
}

export default function AIEditor({ html, onHtmlChange }: AIEditorProps) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<{role: string, content: string}[]>([]);

  const handleSubmit = async () => {
    if (!prompt.trim()) return;

    setLoading(true);
    setHistory(prev => [...prev, { role: 'user', content: prompt }]);

    try {
      // Add timeout using AbortController
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout

      const response = await fetch('/api/edit-website', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          html: html,
          instruction: prompt,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Check response status before parsing JSON
      if (!response.ok) {
        console.error('AI Editor: Response not OK:', response.status);
        let errorMsg = 'Gagal. Cuba lagi.';
        try {
          const errorData = await response.json();
          if (errorData.error === 'Backend error') {
            errorMsg = 'Pelayan sibuk. Cuba lagi dalam beberapa saat.';
          }
        } catch {
          // Response might not be JSON
        }
        setHistory(prev => [...prev, { role: 'assistant', content: errorMsg }]);
        return;
      }

      // Parse JSON response
      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        console.error('AI Editor: JSON parse error:', parseError);
        setHistory(prev => [...prev, {
          role: 'assistant',
          content: 'Ralat memproses respons. Cuba lagi.'
        }]);
        return;
      }

      if (data.success && data.html) {
        onHtmlChange(data.html);
        setHistory(prev => [...prev, {
          role: 'assistant',
          content: 'Perubahan berjaya!'
        }]);
      } else {
        // Show specific error message if available
        const errorMsg = data.error === 'Timeout - cuba lagi'
          ? 'Timeout - cuba lagi dalam beberapa saat.'
          : data.error === 'No API key'
          ? 'API tidak dikonfigurasi. Sila hubungi sokongan.'
          : data.error === 'Missing data'
          ? 'Data tidak lengkap. Cuba lagi.'
          : data.error === 'Failed to extract HTML'
          ? 'AI tidak dapat mengubah HTML. Cuba arahan yang lebih mudah.'
          : data.error === 'API error'
          ? 'Pelayan AI sibuk. Cuba lagi.'
          : 'Gagal. Cuba lagi.';
        setHistory(prev => [...prev, {
          role: 'assistant',
          content: errorMsg
        }]);
      }
    } catch (error) {
      console.error('AI Editor error:', error);
      // Provide more specific error messages
      let errorMsg = 'Ralat rangkaian. Cuba lagi.';
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          errorMsg = 'Timeout - operasi mengambil masa terlalu lama. Cuba lagi.';
        } else if (error.message.includes('fetch')) {
          errorMsg = 'Tidak dapat menghubungi pelayan. Semak sambungan internet anda.';
        }
      }
      setHistory(prev => [...prev, {
        role: 'assistant',
        content: errorMsg
      }]);
    }

    setLoading(false);
    setPrompt('');
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-4">
      <h3 className="font-bold text-lg mb-4">AI Editor</h3>

      {/* Chat History */}
      <div className="h-48 overflow-y-auto mb-4 space-y-2 bg-gray-50 rounded-lg p-3">
        {history.length === 0 && (
          <p className="text-gray-400 text-sm">
            Taip apa yang anda mahu ubah...
            <br/>Contoh: &quot;Tukar warna button jadi merah&quot;
          </p>
        )}
        {history.map((msg, i) => (
          <div key={i} className={`p-2 rounded-lg ${
            msg.role === 'user'
              ? 'bg-blue-100 text-blue-800 ml-8'
              : 'bg-gray-200 text-gray-800 mr-8'
          }`}>
            {msg.content}
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="Contoh: Tukar tajuk jadi 'Kedai Saya'"
          className="flex-1 border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? '...' : 'Ubah'}
        </button>
      </div>

      {/* Quick Actions */}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={() => setPrompt('Tukar warna button jadi merah')}
          className="text-xs bg-gray-100 px-3 py-1 rounded-full hover:bg-gray-200"
        >
          Tukar warna
        </button>
        <button
          onClick={() => setPrompt('Tambah nombor telefon 012-3456789')}
          className="text-xs bg-gray-100 px-3 py-1 rounded-full hover:bg-gray-200"
        >
          Tambah telefon
        </button>
        <button
          onClick={() => setPrompt('Tukar alamat kedai')}
          className="text-xs bg-gray-100 px-3 py-1 rounded-full hover:bg-gray-200"
        >
          Tukar alamat
        </button>
        <button
          onClick={() => setPrompt('Tambah harga baru RM50')}
          className="text-xs bg-gray-100 px-3 py-1 rounded-full hover:bg-gray-200"
        >
          Tambah harga
        </button>
      </div>
    </div>
  );
}
