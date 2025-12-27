import streamlit as st



print_extra_comment = False
def nlp_app(text):
    import nltk
#    nltk.download('punkt')
    from nltk.tokenize import sent_tokenize
    if print_extra_comment:
        print("Paragraph to sentences") 
    sentences = sent_tokenize(text)
    if print_extra_comment:
        for i in sentences:
            print(i)
        print()

    if print_extra_comment:
        print("Removing punctuation")
    import re
    sentences_without_punctuation = []
    for i in sentences:
        temp_text = re.sub(r"[^a-zA-Z0-9]", " ", i) 
        sentences_without_punctuation.append(temp_text)
    if print_extra_comment:
        for i in sentences_without_punctuation:
            print(i)
        print()

    if print_extra_comment:
        print("tokenizing the sentence to words")
    from nltk.tokenize import word_tokenize
    sentences_tokenized = []
    for i in sentences_without_punctuation:
        sentences_tokenized.append(word_tokenize(i))
    if print_extra_comment:
        for i in sentences_tokenized:
            print(i)
        print()  
    if print_extra_comment:
        print("removing stopwords")
#    nltk.download('stopwords')
    from nltk.corpus import stopwords
    sentences_tokenized_without_stopwords = []
    for i in sentences_tokenized:
        temp_ = [w for w in i if w not in stopwords.words("english")]
        sentences_tokenized_without_stopwords.append(temp_)
    if print_extra_comment:
        for i in sentences_tokenized_without_stopwords:
            print(i)
        print()
    if print_extra_comment:
        print("Stemming")
#    nltk.download('wordnet')
    # nltk.download('omw-1.4') #This is needed if we are considering different languages      https://chatgpt.com/c/67040523-0ba8-8009-93ba-f17236ef88a0
    from nltk.stem.porter import PorterStemmer
    sentences_with_lemma = []
    for i in sentences_tokenized_without_stopwords:
        temp_ = [PorterStemmer().stem(w) for w in i]
        sentences_with_lemma.append(temp_)
    if print_extra_comment:
        for i in sentences_with_lemma:
            print(i)
        print()

    final_list_for_next_steps = sentences_tokenized_without_stopwords  #if need, change to "sentences_with_lemma"
    if print_extra_comment:
        print("POS tagging")
#    nltk.download('averaged_perceptron_tagger')
    from nltk import pos_tag
#    nltk.download('words')

    pos_tagged_list = []
    for i in final_list_for_next_steps:
        pos_tagged_list.append(pos_tag(i))
    if print_extra_comment:
        for i in pos_tagged_list:
            print(i)
        print()    
    if print_extra_comment:    
        print("Named entity recognition")
#    nltk.download('maxent_ne_chunker')
    from nltk import ne_chunk
    ner_list = []
    for i in pos_tagged_list:
        ner_list.append(ne_chunk(i))
    if print_extra_comment:
        for i in ner_list:
            print(i)
        print()   
    # # maxent_ne_chunker  vs  averaged_perceptron_tagger    #   https://chatgpt.com/c/67040523-0ba8-8009-93ba-f17236ef88a0
    # # words vs wordnet                                     #   https://chatgpt.com/c/67040523-0ba8-8009-93ba-f17236ef88a0#:~:text=why%20should%20I%20do%20%22nltk.download(%27words%27)%22

    # https://chatgpt.com/c/67041466-8114-8009-b68a-0b6598bca5fe#:~:text=1.-,Sentiment%20Analysis,-Goal%3A%20Determine
        # Also the replies from ChatGPT above and below this are good too

    from textblob import TextBlob

    polarity_scores = []
    subjectivity_scores = []
    positivity_count = 0
    negativity_count = 0
    subjective_count = 0
    objective_count = 0
    for i,j in zip(sentences, ner_list):
        # Create a TextBlob object
        blob = TextBlob(i)

        # Get the sentiment
        sentiment = blob.sentiment
        # st.write(f"Polarity: {sentiment.polarity}, Subjectivity: {sentiment.subjectivity}")
        polarity_scores.append(sentiment.polarity)
        subjectivity_scores.append(sentiment.subjectivity)
        # st.write(sentiment.polarity)
        if sentiment.polarity < 0.0:
            negativity_count = negativity_count + 1
        else:
            positivity_count = positivity_count + 1
            
        if sentiment.subjectivity < 0.5:
            objective_count = objective_count + 1
        else:
            subjective_count = subjective_count + 1
        print()
    st.header("About the text you provided,")
    st.write(text)
    if positivity_count > negativity_count:
        st.success("Overall polarity of the text is Positive")
    else:
        st.warning("Overall polarity of the text is Negative")
    
    if objective_count > subjective_count:
        st.info("Overall text is an Objective text")
    else:
        st.info("Overall text is a Subjective text")
    st.divider()
    
    
    st.write("Sentences vs their Polarity")
    st.bar_chart(data=polarity_scores,x_label="The sentences", y_label="Polarity(Closer to 1 means Positive)")
    st.write("Sentences vs their Subjectivity")
    st.bar_chart(data=subjectivity_scores,x_label="The sentences", y_label="Subjectivity(Closer to 1 means Subjective)")
    
    
    
    st.subheader("Now, let's break down the details sentence by sentence")
    for i,j in zip(sentences, ner_list):
        st.write(i)#, j[1:4])
        # Create a TextBlob object
        blob = TextBlob(i)

        # Get the sentiment
        sentiment = blob.sentiment
        # st.write(f"Polarity: {sentiment.polarity}, Subjectivity: {sentiment.subjectivity}")
        
        if sentiment.polarity < 0.0:
            st.warning("Negative sentence")
        else:
            st.success("Positive sentence")
            
        if sentiment.subjectivity < 0.5:
            st.info("Objective sentence")
        else:
            st.info("Subjective sentence")
        print()
        st.divider()
    

query = st.text_input("Enter the text you need to see the sentiment analysis on:", key='search_input')
if query:
    nlp_app(query)