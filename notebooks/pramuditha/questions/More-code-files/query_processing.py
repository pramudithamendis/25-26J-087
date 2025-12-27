import nltk
import string
from nltk.corpus import wordnet
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# NLTK data files download
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

def preprocess_query(query):
    # Lowercase the query
    query = query.lower()
    # Remove punctuation (keep numbers)
    punctuations = string.punctuation.replace('-', '')
    query = query.translate(str.maketrans('', '', punctuations))
    # Tokenize the query
    tokens = nltk.word_tokenize(query)
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]
    # Lemmatization
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token) for token in tokens]
    # Join tokens back to string
    preprocessed_query = ' '.join(tokens)
    return preprocessed_query

def query_expansion(tokens):
    expanded_tokens = tokens.copy()
    for token in tokens:
        synonyms = wordnet.synsets(token)
        for syn in synonyms:
            for lemma in syn.lemmas():
                expanded_tokens.append(lemma.name())
    # Remove duplicates
    expanded_tokens = list(set(expanded_tokens))
    return expanded_tokens

if __name__ == '__main__':
    query = input("Enter your search query: ")
    preprocessed_query = preprocess_query(query)
    tokens = preprocessed_query.split()
    expanded_tokens = query_expansion(tokens)
    expanded_query = ' '.join(expanded_tokens)
    print("Expanded Query:", expanded_query)