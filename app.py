from flask import Flask, request, render_template
from PyPDF2 import PdfReader
from collections import Counter
import random
import spacy
import nltk
from nltk.corpus import brown
import string

nltk.download('brown')

app = Flask(__name__)

nlp = spacy.load('en_core_web_sm')
freq_dist = nltk.FreqDist(brown.words())

def is_common(word):
    return freq_dist[word.lower()] > 1000 or word.lower() in string.punctuation

def is_significant(word):
    return len(word) > 3

def generate_mcqs(text, num_ques=5):
    if text is None or text.strip() == "":
        return []

    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    if not sentences:
        return []

    selected_sentences = random.sample(sentences, min(num_ques, len(sentences)))
    mcqs = []

    for sentence in selected_sentences:
        sentence = sentence.lower()
        sent_doc = nlp(sentence)
        nouns = [token.text for token in sent_doc if token.pos_ == 'NOUN' and is_significant(token.text) and not is_common(token.text)]
        
        if len(nouns) < 2:
            continue

        noun_counts = Counter(nouns)
        if noun_counts:
            subject = sorted(noun_counts.items(), key=lambda x: x[1], reverse=True)[0][0]
            answer_choices = [subject]

            # Replace subject with blank
            ques = sentence.replace(subject, "______")

            # Collect distractors from the nouns, excluding the subject
            distractors = [word for word in nouns if word != subject]
            if len(distractors) < 3:
                distractors = distractors + random.sample(nouns, 3 - len(distractors))

            # Ensure we have 3 distractors
            random.shuffle(distractors)
            answer_choices.extend(distractors[:3])
            random.shuffle(answer_choices)

            correct_ans = chr(65 + answer_choices.index(subject))
            mcqs.append((ques, answer_choices, correct_ans))

    return mcqs

def process_pdf(file):
    text = ""
    pdf_reader = PdfReader(file)
    for page_num in range(len(pdf_reader.pages)):
        page_text = pdf_reader.pages[page_num].extract_text()
        text += page_text
    return text

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template('index.html')

@app.route("/generate_mcqs", methods=["POST"])
def generate_mcqs_route():
    text = ""
    if 'file[]' in request.files:
        files = request.files.getlist("file[]")
        for file in files:
            if file.filename.endswith('.pdf'):
                text += process_pdf(file)
            else:
                text += file.read().decode('utf-8')
    num_questions = int(request.form['num_ques'])
    mcqs = generate_mcqs(text, num_ques=num_questions)
    mcqs_with_index = [(i+1, mcq) for i, mcq in enumerate(mcqs)]
    return render_template('mcqs.html', mcqs=mcqs_with_index, chr=chr)

if __name__ == "__main__":
    app.run(debug=True)
