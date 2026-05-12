'use client';

// MapControls — bottom-right floating controls.

import { Crosshair, EyeOff, Layers, Minus, Plus } from 'lucide-react';

interface Props {
  showZones: boolean;
  showOfflineRiders: boolean;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onCenterOnOutlet: () => void;
  onToggleZones: () => void;
  onToggleOfflineRiders: () => void;
}

export default function MapControls({
  showZones,
  showOfflineRiders,
  onZoomIn,
  onZoomOut,
  onCenterOnOutlet,
  onToggleZones,
  onToggleOfflineRiders,
}: Props) {
  return (
    <div className="absolute bottom-4 right-4 z-[1000] flex flex-col gap-2">
      <div className="flex flex-col rounded-lg overflow-hidden bg-[#0a0e1a]/95 border border-white/[0.08] backdrop-blur-sm">
        <CtrlButton onClick={onZoomIn} ariaLabel="Zum masuk">
          <Plus size={16} strokeWidth={1.5} />
        </CtrlButton>
        <div className="h-px bg-white/[0.06]" />
        <CtrlButton onClick={onZoomOut} ariaLabel="Zum keluar">
          <Minus size={16} strokeWidth={1.5} />
        </CtrlButton>
      </div>
      <CtrlButton onClick={onCenterOnOutlet} ariaLabel="Pusat ke outlet" rounded>
        <Crosshair size={16} strokeWidth={1.5} />
      </CtrlButton>
      <CtrlButton
        onClick={onToggleZones}
        ariaLabel="Togol zon"
        rounded
        active={showZones}
      >
        <Layers size={16} strokeWidth={1.5} />
      </CtrlButton>
      <CtrlButton
        onClick={onToggleOfflineRiders}
        ariaLabel="Togol rider offline"
        rounded
        active={showOfflineRiders}
      >
        <EyeOff size={16} strokeWidth={1.5} />
      </CtrlButton>
    </div>
  );
}

function CtrlButton({
  onClick,
  ariaLabel,
  rounded,
  active,
  children,
}: {
  onClick: () => void;
  ariaLabel: string;
  rounded?: boolean;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      title={ariaLabel}
      className={`h-11 w-11 flex items-center justify-center transition ${
        rounded
          ? 'rounded-lg bg-[#0a0e1a]/95 border border-white/[0.08] backdrop-blur-sm'
          : ''
      } ${
        active
          ? 'text-[#C7FF3D]'
          : 'text-white/70 hover:text-white hover:bg-white/[0.06]'
      }`}
    >
      {children}
    </button>
  );
}
