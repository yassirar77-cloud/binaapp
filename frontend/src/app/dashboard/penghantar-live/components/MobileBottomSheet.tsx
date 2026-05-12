'use client';

// MobileBottomSheet — wraps OrdersPanel + RidersPanel with two tabs.
// Two states: peek (60px header bar only) and expanded (60vh).
// Tap header chevron to toggle. TODO v2: vertical drag to expand.

import { useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import type { ActiveOrder, LiveRider } from '../lib/types';
import OrdersPanel from './OrdersPanel';
import RidersPanel from './RidersPanel';

type Tab = 'orders' | 'riders';

interface Props {
  orders: ActiveOrder[];
  riders: LiveRider[];
  selectedOrderId: string | null;
  selectedRiderId: string | null;
  stuckOrderIds: ReadonlySet<string>;
  showOffline: boolean;
  onSelectOrder: (id: string) => void;
  onSelectRider: (id: string) => void;
}

export default function MobileBottomSheet({
  orders,
  riders,
  selectedOrderId,
  selectedRiderId,
  stuckOrderIds,
  showOffline,
  onSelectOrder,
  onSelectRider,
}: Props) {
  const [tab, setTab] = useState<Tab>('orders');
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`phl-mobile-sheet fixed left-0 right-0 bottom-0 z-[1050] bg-[#0a0e1a] border-t border-white/[0.08] flex flex-col ${
        expanded ? 'h-[60vh]' : 'h-[58px]'
      }`}
    >
      <div className="flex items-stretch border-b border-white/[0.06]">
        <button
          type="button"
          onClick={() => {
            setTab('orders');
            setExpanded(true);
          }}
          className={`flex-1 h-[58px] flex items-center justify-center gap-2 text-sm font-geist transition ${
            tab === 'orders'
              ? 'text-white border-b-2 border-[#C7FF3D]'
              : 'text-white/60'
          }`}
        >
          Pesanan
          <span className="font-mono text-[11px] text-white/40">
            {orders.length}
          </span>
          {stuckOrderIds.size > 0 && (
            <span className="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-red-400" />
          )}
        </button>
        <button
          type="button"
          onClick={() => {
            setTab('riders');
            setExpanded(true);
          }}
          className={`flex-1 h-[58px] flex items-center justify-center gap-2 text-sm font-geist transition ${
            tab === 'riders'
              ? 'text-white border-b-2 border-[#C7FF3D]'
              : 'text-white/60'
          }`}
        >
          Rider
          <span className="font-mono text-[11px] text-white/40">
            {riders.length}
          </span>
        </button>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-label={expanded ? 'Tutup senarai' : 'Buka senarai'}
          className="w-12 flex items-center justify-center text-white/60 hover:text-white"
        >
          {expanded ? (
            <ChevronDown size={18} strokeWidth={1.5} />
          ) : (
            <ChevronUp size={18} strokeWidth={1.5} />
          )}
        </button>
      </div>

      {expanded && (
        <div className="flex-1 min-h-0">
          {tab === 'orders' ? (
            <OrdersPanel
              orders={orders}
              selectedId={selectedOrderId}
              stuckOrderIds={stuckOrderIds}
              onSelect={(id) => {
                onSelectOrder(id);
                setExpanded(false);
              }}
            />
          ) : (
            <RidersPanel
              riders={riders}
              selectedId={selectedRiderId}
              showOffline={showOffline}
              onSelect={(id) => {
                onSelectRider(id);
                setExpanded(false);
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
