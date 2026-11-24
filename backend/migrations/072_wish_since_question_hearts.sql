-- Migration 072: mysyg.com wishes — "since" counter, secret question, hearts
--
-- Three small things around the gift itself:
--
--   since_kind   "Bersama sejak 14 Februari 2020." The gift page counts the
--   since_date   days from a date the sender chose and ticks the seconds.
--                since_kind is one of the keys in SINCE_KINDS
--                (services/wishes.py); the wording is code, so it is free
--                text here for the same reason `package` is.
--
--   secret_question     The box opens only for someone who can answer the
--   secret_answer_hash  sender's question. Until then the backend withholds
--   secret_hint         the message, photos and video, exactly as it does
--                       for a timed seal. The answer is never stored: only
--                       SHA-256("answer:<slug>:<normalised answer>").
--
--   heart_count  Hearts the recipient tapped back, shown to the sender.
--
-- All nullable / defaulted, so existing wishes are unaffected. Still
-- backend-only: RLS stays on with no policies (migration 062).

ALTER TABLE public.wishes
    ADD COLUMN IF NOT EXISTS since_kind         TEXT,
    ADD COLUMN IF NOT EXISTS since_date         DATE,
    ADD COLUMN IF NOT EXISTS secret_question    TEXT,
    ADD COLUMN IF NOT EXISTS secret_answer_hash TEXT,
    ADD COLUMN IF NOT EXISTS secret_hint        TEXT,
    ADD COLUMN IF NOT EXISTS heart_count        INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.wishes DROP CONSTRAINT IF EXISTS wishes_secret_question_check;
ALTER TABLE public.wishes
    ADD CONSTRAINT wishes_secret_question_check
    CHECK (
        (secret_question IS NULL OR char_length(secret_question) <= 120)
        AND (secret_hint IS NULL OR char_length(secret_hint) <= 80)
        -- a question without an answer could never be opened
        AND ((secret_question IS NULL) = (secret_answer_hash IS NULL))
    );

ALTER TABLE public.wishes DROP CONSTRAINT IF EXISTS wishes_heart_count_check;
ALTER TABLE public.wishes
    ADD CONSTRAINT wishes_heart_count_check
    CHECK (heart_count BETWEEN 0 AND 99999);
