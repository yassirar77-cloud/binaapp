# Dashboard Tab Audit

## Profile Page: `frontend/src/app/profile/page.tsx`

### Tab System
- State variable: `activeTab` with type `'websites' | 'orders' | 'riders' | 'chat'`
- Default: `'websites'`
- Tab buttons: Scrollable flex container with `overflow-x-auto`
- Tab content: Conditional rendering `{activeTab === 'xxx' && (...)}`
- Tab button class pattern:
  - Active: `text-blue-600 border-b-2 border-blue-600`
  - Inactive: `text-gray-500 hover:text-gray-700`

### Auth
- Uses custom BinaApp token system + Supabase fallback
- `supabase` from `@/lib/supabase` (can be null)
- `getStoredToken()`, `getCurrentUser()`, `getApiAuthToken()` also exported

### Existing Imports
- `useState, useEffect` from react
- `useRouter` from next/navigation
- `Link` from next/link
- `supabase, getApiAuthToken, getCurrentUser, getStoredToken, signOut` from `@/lib/supabase`
- `User` from `@supabase/supabase-js`
- `dynamic` from `next/dynamic`
- Dynamic: `OwnerChatDashboard`, `AnimatedUsageWidget`

### Existing State
- `websites` - array of user's websites
- `orders` - array of delivery orders
- `riders` - array of riders
- `user` - current authenticated user

### Supabase Tables Queried
- `profiles` - user profile data
- `websites` - user's websites
- `delivery_orders` with `order_items` - order data

### Website IDs
- `websites.map(w => w.id)` used to query related data

## Dependencies
- `recharts` already installed: `^2.12.0`
- No additional installs needed

## Supabase Client
- File: `frontend/src/lib/supabase.ts`
- Export: `export const supabase = ...` (can be null if env vars missing)
- Import pattern: `import { supabase } from '@/lib/supabase'`
