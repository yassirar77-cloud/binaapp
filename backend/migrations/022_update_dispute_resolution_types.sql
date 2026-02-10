-- Migration 022: Update dispute resolution types for owner complaints against BinaApp
-- The resolve modal now uses owner complaint resolution types instead of customer-order refund types.
-- Old resolution types are kept for backward compatibility with existing records.

-- Drop existing constraint if any
ALTER TABLE ai_disputes DROP CONSTRAINT IF EXISTS ai_disputes_resolution_type_check;

-- Add updated constraint that accepts both new and legacy resolution types
ALTER TABLE ai_disputes ADD CONSTRAINT ai_disputes_resolution_type_check
CHECK (resolution_type IS NULL OR resolution_type IN (
  -- New owner complaint resolution types
  'issue_resolved',
  'self_resolved',
  'no_longer_needed',
  'accepted_explanation',
  'still_unsatisfied',
  'withdraw_complaint',
  -- Legacy values for backward compatibility with existing records
  'full_refund',
  'partial_refund',
  'replacement',
  'credit',
  'apology',
  'rejected',
  'escalated'
));
