import pickle
from sklearn.feature_extraction.text import TfidfVectorizer

def load_preprocessed_documents():
    with open('preprocessed_documents.pkl', 'rb') as f:
        preprocessed_documents = pickle.load(f)
    return preprocessed_documents

def vectorize_documents(preprocessed_documents):
    # Create a list of document texts
    documents = list(preprocessed_documents.values())
    doc_ids = list(preprocessed_documents.keys())
    # Initialize TfidfVectorizer with appropriate parameters
    vectorizer = TfidfVectorizer()
    # Fit and transform the documents
    tfidf_matrix = vectorizer.fit_transform(documents)   #documents is as  ["Content of doc1", "Content of doc2"]
    # Save the vectorizer and tfidf_matrix for later use
    with open('tfidf_vectorizer.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)
    with open('tfidf_matrix.pkl', 'wb') as f:
        pickle.dump((tfidf_matrix, doc_ids), f)

if __name__ == '__main__':
    preprocessed_documents = load_preprocessed_documents()
    vectorize_documents(preprocessed_documents)