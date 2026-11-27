# How an agent uses pdfforge

Translate the user's words into ops. `pdfforge ops` lists every operation with its parameters, so there is nothing to guess. Examples:

- "keep only the first three pages" -> extract_pages
- "stamp DRAFT on every page" -> watermark
- "join these three PDFs" -> merge
- "split it into one file per page" -> split
- "number the pages" -> page_numbers
- "what is in this file?" -> describe, read

If the user asks for something that is not an op yet, add it — see CONTRIBUTING.md. That is the whole point: the tool grows with what people ask for.
