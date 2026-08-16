// Rider vehicle type labels (Bahasa Malaysia)

export const VEHICLE_TYPE_LABELS: Record<string, string> = {
  motorcycle: 'Motosikal',
  car: 'Kereta',
  bicycle: 'Basikal',
  scooter: 'Skuter',
};

export const VEHICLE_TYPE_OPTIONS: ReadonlyArray<{
  value: string;
  label: string;
}> = [
  { value: 'motorcycle', label: 'Motosikal' },
  { value: 'car', label: 'Kereta' },
  { value: 'bicycle', label: 'Basikal' },
  { value: 'scooter', label: 'Skuter' },
];

export function vehicleTypeLabel(type: string | null | undefined): string {
  if (!type) return '—';
  return VEHICLE_TYPE_LABELS[type] ?? type;
}
