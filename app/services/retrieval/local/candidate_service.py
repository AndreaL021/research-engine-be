from app.schemas.research_schema import RetrievedChunkSchema


def select_reranker_candidates(
    documents: list[RetrievedChunkSchema],
    limit: int,
):
    # First pass favors source diversity; second pass fills remaining slots with
    # the best leftover chunks regardless of URL.
    selected_documents = []
    selected_urls = set()

    for document in documents:
        if document.url in selected_urls:
            continue

        selected_documents.append(document)
        selected_urls.add(document.url)

        if len(selected_documents) >= limit:
            return selected_documents

    selected_document_ids = {
        id(document)
        for document in selected_documents
    }

    for document in documents:
        if id(document) in selected_document_ids:
            continue

        selected_documents.append(document)

        if len(selected_documents) >= limit:
            break

    return selected_documents


def assign_source_numbers(
    documents: list[RetrievedChunkSchema],
):
    return [
        document.model_copy(
            update={
                "source_number": index + 1
            }
        )
        for index, document in enumerate(documents)
    ]
