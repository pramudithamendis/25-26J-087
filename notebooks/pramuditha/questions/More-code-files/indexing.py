import pickle
import math
from collections import defaultdict

def load_preprocessed_documents():
    with open('preprocessed_documents.pkl', 'rb') as f:
        preprocessed_documents = pickle.load(f)
    return preprocessed_documents

def build_inverted_index(preprocessed_documents):
    inverted_index = defaultdict(dict)
    doc_term_counts = {}
    total_documents = len(preprocessed_documents)

    # Build inverted index and term frequencies
    for doc_id, terms in preprocessed_documents.items():
        term_counts = {}
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        doc_term_counts[doc_id] = term_counts
        for term, count in term_counts.items():
            if doc_id not in inverted_index[term]:
                inverted_index[term][doc_id] = count
                
    idf = {}
    for term, doc_list in inverted_index.items():
        idf[term] = math.log(total_documents / len(doc_list))

    return inverted_index, idf, doc_term_counts

if __name__ == '__main__':
    preprocessed_documents = load_preprocessed_documents()
    inverted_index, idf, doc_term_counts = build_inverted_index(preprocessed_documents)
    
    # Save for later use
    with open('inverted_index.pkl', 'wb') as f:
        pickle.dump(inverted_index, f)
    with open('idf.pkl', 'wb') as f:
        pickle.dump(idf, f)
    with open('doc_term_counts.pkl', 'wb') as f:
        pickle.dump(doc_term_counts, f)