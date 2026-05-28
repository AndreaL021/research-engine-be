def chunk_content(
    content: str,
    chunk_size: int = 200,
    overlap: int = 50,
) -> list[str]:
    words = content.split()

    chunks: list[str] = []

    step = chunk_size - overlap

    for start in range(0, len(words), step):

        end = start + chunk_size

        chunk_words = words[start:end]

        if not chunk_words:
            continue

        chunk = " ".join(chunk_words)

        chunks.append(chunk)

    return chunks