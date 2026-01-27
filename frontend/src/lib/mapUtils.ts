/**
 * Map Utility Functions
 * Used for delivery distance and fee calculations
 */

/**
 * Calculate distance between two points using Haversine formula
 * @param lat1 - Latitude of first point
 * @param lon1 - Longitude of first point
 * @param lat2 - Latitude of second point
 * @param lon2 - Longitude of second point
 * @returns Distance in kilometers
 */
export function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371; // Earth's radius in kilometers
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distance = R * c;
  return Math.round(distance * 100) / 100; // Round to 2 decimal places
}

/**
 * Convert degrees to radians
 */
function toRad(deg: number): number {
  return deg * (Math.PI / 180);
}

/**
 * Calculate delivery fee based on distance
 * @param distanceKm - Distance in kilometers
 * @returns Delivery fee in MYR
 */
export function calculateDeliveryFee(distanceKm: number): number {
  // Base fee structure:
  // - First 3km: RM 3.00 base
  // - 3-5km: RM 1.00 per km
  // - 5-10km: RM 1.50 per km
  // - 10km+: RM 2.00 per km

  const baseFee = 3.0;
  let additionalFee = 0;

  if (distanceKm <= 3) {
    // Base fee only
    additionalFee = 0;
  } else if (distanceKm <= 5) {
    // RM 1.00 per km for 3-5km
    additionalFee = (distanceKm - 3) * 1.0;
  } else if (distanceKm <= 10) {
    // RM 1.00 for 3-5km + RM 1.50 for 5-10km
    additionalFee = 2 * 1.0 + (distanceKm - 5) * 1.5;
  } else {
    // RM 1.00 for 3-5km + RM 1.50 for 5-10km + RM 2.00 for 10km+
    additionalFee = 2 * 1.0 + 5 * 1.5 + (distanceKm - 10) * 2.0;
  }

  const totalFee = baseFee + additionalFee;
  return Math.round(totalFee * 100) / 100; // Round to 2 decimal places
}

/**
 * Format distance for display
 * @param distanceKm - Distance in kilometers
 * @returns Formatted distance string
 */
export function formatDistance(distanceKm: number): string {
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)} m`;
  }
  return `${distanceKm.toFixed(1)} km`;
}

/**
 * Format delivery fee for display
 * @param fee - Fee in MYR
 * @returns Formatted fee string
 */
export function formatDeliveryFee(fee: number): string {
  return `RM ${fee.toFixed(2)}`;
}
