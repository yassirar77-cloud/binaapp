-- Migration 069: mysyg.com wishes — timed unlock, opens, and the reply
--
-- Three things the sender asked for after "is it ready?":
--
--   unlock_at    "Open it at midnight on her birthday." Until this moment the
--                gift page shows a sealed box and a countdown, and the backend
--                withholds the message, photos and video entirely (they are
--                not in the page source or the public API). NULL = open now.
--
--   opened_at    "Did she see it?" Set the first time the recipient taps the
--   open_count   gift box; open_count counts every tap after that. The page
--                view counter (view_count) is a different thing: link
--                previews and crawlers load the page without opening the box.
--
--   reaction     "What did she say?" The recipient may send back one emoji
--   reply_text   reaction and a short note. One reply per wish; sending again
--   replied_at   replaces it. Shown only on the sender's secret status page.
--
-- All nullable / defaulted, so existing wishes are unaffected. Still
-- backend-only: RLS stays on with no policies (migration 062).

ALTER TABLE public.wishes
    ADD COLUMN IF NOT EXISTS unlock_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS opened_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS open_count  INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reaction    TEXT,
    ADD COLUMN IF NOT EXISTS reply_text  TEXT,
    ADD COLUMN IF NOT EXISTS replied_at  TIMESTAMPTZ;

ALTER TABLE public.wishes DROP CONSTRAINT IF EXISTS wishes_reaction_check;
ALTER TABLE public.wishes
    ADD CONSTRAINT wishes_reaction_check
    CHECK (reaction IS NULL OR reaction IN ('love', 'touched', 'hug', 'laugh', 'wow'));

ALTER TABLE public.wishes DROP CONSTRAINT IF EXISTS wishes_reply_text_check;
ALTER TABLE public.wishes
    ADD CONSTRAINT wishes_reply_text_check
    CHECK (reply_text IS NULL OR char_length(reply_text) <= 300);
