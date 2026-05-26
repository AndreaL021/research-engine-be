from ddgs import DDGS

import trafilatura


async def retrieve_documents(query: str):

    documents = []

    with DDGS() as ddgs:

        results = ddgs.text(query, max_results=5)

        for result in results:

            url = result.get("href")

            try:

                downloaded = trafilatura.fetch_url(url)

                content = trafilatura.extract(downloaded)
                
                if not content:
                    content = result.get("body")

                documents.append(
                    {
                        "title": result.get("title"),
                        "url": url,
                        "content": content,
                    }
                )

            except Exception as error:

                print(error)

    return documents