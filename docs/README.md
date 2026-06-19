# Knowledge base documents

Drop your own oceanography references here as **`.txt`** or **`.md`** files.
On the next question, FloatChat will:

1. Read every `.txt`/`.md` file in this folder,
2. Split it into ~900-character chunks (on paragraph boundaries),
3. Embed the chunks (Gemini `text-embedding-004`) into the vector store, and
4. Use them — alongside the built-in curated docs — to answer conceptual
   questions, citing the file name as the source.

Notes:
- A markdown heading (`# Title`) at the top of a chunk becomes its citation
  title; otherwise the file name is used.
- The embedded index is cached in `../data/rag_index.json` and is rebuilt
  automatically whenever you add, edit, or remove files here.
- Without a `GEMINI_API_KEY`, retrieval falls back to keyword search over these
  same files, so they still work offline.
