import streamlit as st
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from query_processing import preprocess_query, query_expansion
import os
import streamlit.components.v1 as components

# Load the vectorizer and TF-IDF matrix
@st.cache_resource
def load_vectorizer_and_matrix():
    with open('tfidf_vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
    with open('tfidf_matrix.pkl', 'rb') as f:
        tfidf_matrix, doc_ids = pickle.load(f)
    return vectorizer, tfidf_matrix, doc_ids

vectorizer, tfidf_matrix, doc_ids = load_vectorizer_and_matrix()

# Load document snippets
@st.cache_resource
def load_document_snippets():
    with open('doc_snippets.pkl', 'rb') as f:
        doc_snippets = pickle.load(f)
    return doc_snippets

doc_snippets = load_document_snippets()

# Set the path to your PDF documents
pdf_folder_path = './static/pdfs'  # Update this path accordingly

# Set the base URL for PDFs served by the HTTP server
pdf_base_url = 'http://localhost:8502/static/pdfs'  # Adjust this to match your HTTP server

def main():
    if 'results' not in st.session_state:
        st.session_state['results'] = None

    st.title("Document Search Engine")

    # Inject JavaScript to handle keyboard shortcuts
    components.html("""
        <script>
            const docSearchInput = window.parent.document.querySelectorAll('input[type=text]')[0];
            window.parent.document.addEventListener('keydown', function(e) {
                // Check if the input field is not focused
                if (document.activeElement !== docSearchInput) {
                    // Keyboard shortcuts
                    // Focus on input field when '/' is pressed
                    if (e.key === '/') {
                        e.preventDefault();
                        docSearchInput.focus();
                    }
                    // Open PDFs with numbers 1 to 5
                    if (['1', '2', '3', '4', '5'].includes(e.key)) {
                        e.preventDefault();
                        const index = parseInt(e.key) - 1;
                        const links = window.parent.document.querySelectorAll('a.pdf-link');
                        if (links.length > index) {
                            window.open(links[index].href, '_blank');
                        }
                    }
                }
            });
        </script>
        """,
        height=0,
    )

    with st.form(key='search_form'):
        query = st.text_input("Enter your search query:", key='search_input', value ="")
        num_results = st.selectbox("Number of results to display:", options=range(1, 11), index=4)
        submit_button = st.form_submit_button(label='Search')

    if submit_button:
        if query:
            # Process the query
            preprocessed_query = preprocess_query(query)
            tokens = preprocessed_query.split()
            expanded_tokens = query_expansion(tokens)
            expanded_query = ' '.join(expanded_tokens)

            # Transform the query using the vectorizer
            query_vector = vectorizer.transform([expanded_query])
            # print(tfidf_matrix.shape)

            # Compute similarity scores
            similarity_scores = cosine_similarity(query_vector, tfidf_matrix)[0]   #This is going to calc the cosine similarity between the query_vector row with each of the other 25 rows(ie 25 docs). 
                                                                                   #And note that, the cols are the vocab. To view it, use 
                                                                                        # print(vectorizer.get_feature_names_out()) 
            # print(similarity_scores)

            # Rank documents
            doc_scores = list(zip(doc_ids, similarity_scores))
            ranked_docs = sorted(doc_scores, key=lambda x: x[1], reverse=True)
            
            # Store the results in st.session_state
            st.session_state['results'] = {
                'ranked_docs': ranked_docs,
                'num_results': num_results
            }

            display_results = True
        else:
            st.warning("Please enter a query.")
            display_results = False
    else:
        # If not submit_button, check if we have results in session_state
        if st.session_state['results'] is not None:
            ranked_docs = st.session_state['results']['ranked_docs']
            num_results = st.session_state['results']['num_results']
            display_results = True
        else:
            display_results = False

    # Display results if available
    if display_results:
        st.header("Search Results")
        results_found = False
        
        #Metrics about the IR system
        # st.write("------------------------------------------------------------------------")
        # st.write(ranked_docs)
        # st.write("------------------------------------------------------------------------")
        
        # for doc in ranked_docs:
            # st.write(doc[0])
        # thinking the query is "tower place"
        y_actual = ["Burj Khalifa.pdf", "Eiffel Tower.pdf"]
        y_true = [1 if doc[0] in y_actual else 0 for doc in ranked_docs]
        y_pred = [1] * len(ranked_docs)
        
        from sklearn.metrics import precision_score, recall_score, f1_score

        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        # st.write(f"Precision: {precision}, Recall: {recall}, F1-Score: {f1}")

        for idx, (doc_id, score) in enumerate(ranked_docs[:num_results]):
            if score > 0:
                results_found = True
                doc_path = os.path.join(pdf_folder_path, doc_id)
                pdf_url = f"{pdf_base_url}/{doc_id}"

                st.write(f"**Document {idx + 1}:** {doc_id}")
                st.write(f"**Relevance Score:** {score:.4f}")

                # Display snippet
                snippet = doc_snippets.get(doc_id, "")
                st.write(snippet)

                # Open PDF link (old design)
                # Create two columns for buttons
                button_col1, button_col2 = st.columns([1, 1])

                with button_col1:
                    # Open PDF button styled with HTML
                    st.markdown(
                        f'<a href="{pdf_url}" target="_blank" class="pdf-link"><button style="width:100%">Open PDF</button></a>',
                        unsafe_allow_html=True
                    )
                with button_col2:
                    # Download PDF button
                    with open(doc_path, 'rb') as f:
                        pdf_data = f.read()
                    st.download_button(
                        label="Download PDF",
                        data=pdf_data,
                        file_name=doc_id,
                        mime='application/pdf'
                    )

                    # Add divider
                    st.markdown('---')
            else:
                break
        if not results_found:
            st.write("No relevant documents found.")

if __name__ == '__main__':
    main()
