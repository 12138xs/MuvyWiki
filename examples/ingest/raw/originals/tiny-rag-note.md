# Tiny RAG Note

TinyRagDemo is a small teaching project that combines retrieval with generation.

The project keeps documents in a local folder, embeds them into a vector index, retrieves the top matching chunks for a question, and asks a language model to answer with those chunks as context.

The note claims that retrieval-augmented generation is most useful when the answer depends on changing or private documents. It also warns that poor chunking can make retrieval look correct while hiding missing evidence.
