-- Enable realtime for chat tables
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_conversations;

-- Ensure RLS is enabled
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_conversations ENABLE ROW LEVEL SECURITY;

-- Allow public read/write for chat (adjust as needed)
DROP POLICY IF EXISTS "Allow all chat_messages" ON public.chat_messages;
CREATE POLICY "Allow all chat_messages" ON public.chat_messages
FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all chat_conversations" ON public.chat_conversations;
CREATE POLICY "Allow all chat_conversations" ON public.chat_conversations
FOR ALL USING (true) WITH CHECK (true);
