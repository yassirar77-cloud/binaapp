'use client';

import { useEffect, useState } from 'react';

interface Step {
  text: string;
  status: 'pending' | 'loading' | 'done' | 'error';
}

interface ProgressIndicatorProps {
  steps: Step[];
  theme?: string;
}

export default function ProgressIndicator({ steps, theme }: ProgressIndicatorProps) {
  return (
    <div className="space-y-2">
      {theme && (
        <div className="p-3 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎨</span>
            <span className="font-semibold text-purple-700">{theme}</span>
          </div>
        </div>
      )}

      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-3 text-sm">
          {step.status === 'loading' && (
            <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
          )}
          {step.status === 'done' && (
            <span className="text-green-500 font-bold">✓</span>
          )}
          {step.status === 'error' && (
            <span className="text-red-500 font-bold">×</span>
          )}
          {step.status === 'pending' && (
            <span className="text-gray-300">○</span>
          )}
          <span className={`${step.status === 'done' ? 'text-gray-600' : step.status === 'loading' ? 'text-blue-600 font-medium' : 'text-gray-400'}`}>
            {step.text}
          </span>
        </div>
      ))}
    </div>
  );
}
