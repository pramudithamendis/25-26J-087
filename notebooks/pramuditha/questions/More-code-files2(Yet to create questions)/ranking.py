import pickle
from sklearn.metrics.pairwise import cosine_similarity
from query_processing import preprocess_query, query_expansion

def load_vectorizer_and_matrix():
    with open('tfidf_vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
    with open('tfidf_matrix.pkl', 'rb') as f:
        tfidf_matrix, doc_ids = pickle.load(f)
    return vectorizer, tfidf_matrix, doc_ids

def process_query(vectorizer):
    query = input("Enter your search query: ")
    preprocessed_query = preprocess_query(query)
    tokens = preprocessed_query.split()
    expanded_tokens = query_expansion(tokens)
    expanded_query = ' '.join(expanded_tokens)

    # Transform the query using the same vectorizer
    query_vector = vectorizer.transform([expanded_query])
    return query_vector

def compute_similarity(query_vector, tfidf_matrix):
    # Compute cosine similarity between query and documents
    similarity_scores = cosine_similarity(query_vector, tfidf_matrix)
    return similarity_scores[0]

def rank_documents(similarity_scores, doc_ids):
    # Pair document IDs with their similarity scores
    doc_scores = list(zip(doc_ids, similarity_scores))
    # Sort documents by similarity score in descending order
    ranked_docs = sorted(doc_scores, key=lambda x: x[1], reverse=True)
    return ranked_docs

if __name__ == '__main__':
    # Load the vectorizer and TF-IDF matrix
    vectorizer, tfidf_matrix, doc_ids = load_vectorizer_and_matrix()
    # Process the query
    query_vector = process_query(vectorizer)
    # Compute similarity scores
    similarity_scores = compute_similarity(query_vector, tfidf_matrix)
    # Rank documents
    ranked_docs = rank_documents(similarity_scores, doc_ids)
    # Display the results
    print("\nTop matching documents:")
    for doc_id, score in ranked_docs[:10]:
        print(f"{doc_id}: {score}")