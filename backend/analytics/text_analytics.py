
import re
import math
import pandas as pd

from collections import Counter
from wordcloud import WordCloud

from backend.analytics.classification_analytics import (
    DIMENSIONS,
    parse_labels
)


# ============================================================
# CONFIGURATION
# ============================================================

TEXT_COLUMN = "review_text"

CUSTOM_STOPWORDS = {
    "app", "application", "paypal", "use", "using",
    "used", "get", "got", "one", "also", "would",
    "could", "please", "really", "even", "still",
    "much", "many", "make", "made", "want", "need",
    "know", "like", "good", "bad", "great", "worst",
    "best", "thank", "thanks", "dear", "hello",
    "hi", "im", "ive", "dont", "doesnt", "cant",
    "wont", "didnt", "isnt", "wasnt", "thats",
    "its", "youre", "theyre", "there", "today",
    "yesterday"
}

# Common English stopwords, defined locally.
ENGLISH_STOPWORDS = set("""
a about above after again against all am an and any are
as at be because been before being below between both
but by can could did do does doing down during each few
for from further had has have having he her here hers
herself him himself his how i if in into is it its itself
just me more most my myself no nor not now of off on once
only or other our ours ourselves out over own same she
should so some such than that the their theirs them
themselves then there these they this those through to
too under until up very was we were what when where which
while who whom why will with would you your yours yourself
yourselves
""".split())

STOPWORDS = (
    ENGLISH_STOPWORDS.union(CUSTOM_STOPWORDS)
    - {"no", "not", "never"}
)

# ============================================================
# 1. TEXT PREPARATION
# ============================================================


def clean_text(value):

    if pd.isna(value):
        return ""

    value = str(value).lower()

    # Normalize Unicode apostrophes
    value = value.replace("’", "'").replace("‘", "'")

    # Normalize common contractions
    contractions = {
        "don't": "do not",
        "doesn't": "does not",
        "didn't": "did not",
        "can't": "cannot",
        "couldn't": "could not",
        "wouldn't": "would not",
        "shouldn't": "should not",
        "won't": "will not",
        "isn't": "is not",
        "aren't": "are not",
        "wasn't": "was not",
        "weren't": "were not",
        "haven't": "have not",
        "hasn't": "has not",
        "hadn't": "had not",
        "i'm": "i am",
        "i've": "i have",
        "i'll": "i will",
        "you're": "you are",
        "they're": "they are",
        "it's": "it is"
    }

    for contraction, expanded in contractions.items():
        value = value.replace(contraction, expanded)

    # Handle malformed apostrophes and missing apostrophes
    value = re.sub(r"\bdon[^a-z0-9]*t\b", "do not", value)
    value = re.sub(r"\bdoesn[^a-z0-9]*t\b", "does not", value)
    value = re.sub(r"\bwon[^a-z0-9]*t\b", "will not", value)

    # Remove URLs and email addresses
    value = re.sub(r"https?://\S+|www\.\S+", " ", value)
    value = re.sub(r"\S+@\S+", " ", value)

    # Remove punctuation and normalize whitespace
    value = re.sub(r"[^a-z0-9\s]", " ", value)

    return re.sub(r"\s+", " ", value).strip()


def tokenize_text(value, remove_stopwords=True):

    words = re.findall(
        r"\b[a-z][a-z0-9]+\b",
        str(value).lower()
    )

    if remove_stopwords:
        words = [
            word for word in words
            if (word not in STOPWORDS or word in {"no", "not", "never"}) and (len(word) > 2 or word == "no")
        ]

    return words


def prepare_text(df, text_column=TEXT_COLUMN):

    if text_column not in df.columns:
        raise ValueError(
            f"Missing text column: {text_column}"
        )

    working = df.copy()

    working[text_column] = (
        working[text_column]
        .fillna("")
        .astype(str)
    )

    working["cleaned_text"] = (
        working[text_column].apply(clean_text)
    )

    return working


# ============================================================
# 2. FREQUENT KEYWORDS
# ============================================================

def get_top_keywords(
    df,
    top_n=30,
    text_column="cleaned_text"
):

    if text_column not in df.columns:
        df = prepare_text(df)

    counter = Counter()

    for text in df[text_column].fillna("").astype(str):
        counter.update(tokenize_text(text))

    return pd.DataFrame(
        counter.most_common(top_n),
        columns=["keyword", "frequency"]
    )


# ============================================================
# 3. N-GRAM ANALYSIS
# ============================================================

def get_top_ngrams(
    df,
    ngram_range=(1, 2),
    top_n=30,
    min_df=2,
    text_column="cleaned_text"
):

    if text_column not in df.columns:
        df = prepare_text(df)

    if (
        len(ngram_range) != 2
        or ngram_range[0] < 1
        or ngram_range[1] < ngram_range[0]
    ):
        raise ValueError("Invalid ngram_range.")

    term_frequency = Counter()
    document_frequency = Counter()

    for text in df[text_column].fillna("").astype(str):

        tokens = tokenize_text(text)
        document_terms = set()

        for n in range(ngram_range[0], ngram_range[1] + 1):

            terms = [
                " ".join(tokens[i:i+n])
                for i in range(len(tokens) - n + 1)
            ]

            term_frequency.update(terms)
            document_terms.update(terms)

        document_frequency.update(document_terms)

    results = [
        (term, frequency)
        for term, frequency in term_frequency.items()
        if document_frequency[term] >= min_df
    ]

    return pd.DataFrame(
        sorted(results, key=lambda x: x[1], reverse=True)[:top_n],
        columns=["phrase", "frequency"]
    )


# ============================================================
# 4. TF-IDF WITHOUT SCIKIT-LEARN
# ============================================================

def get_tfidf_keywords(
    df,
    top_n=30,
    min_df=2,
    text_column="cleaned_text"
):
    """
    Calculate corpus-level TF-IDF scores using pure Python.

    TF = term frequency within a document.
    IDF = log((N + 1) / (DF + 1)) + 1.

    Scores are summed across documents, so this ranks
    terms by their overall TF-IDF contribution.
    """

    if text_column not in df.columns:
        df = prepare_text(df)

    documents = [
        tokenize_text(text)
        for text in df[text_column].fillna("").astype(str)
    ]

    documents = [doc for doc in documents if doc]

    if not documents:
        return pd.DataFrame(
            columns=["keyword", "tfidf_score"]
        )

    total_documents = len(documents)

    document_frequency = Counter()

    for document in documents:
        document_frequency.update(set(document))

    scores = Counter()

    for document in documents:

        term_counts = Counter(document)
        total_terms = len(document)

        for term, count in term_counts.items():

            df_count = document_frequency[term]

            if df_count < min_df:
                continue

            tf = count / total_terms

            idf = (
                math.log(
                    (total_documents + 1) / (df_count + 1)
                ) + 1
            )

            scores[term] += tf * idf

    return pd.DataFrame(
        scores.most_common(top_n),
        columns=["keyword", "tfidf_score"]
    )


# ============================================================
# 5. WORD CLOUD
# ============================================================

def generate_wordcloud(
    df,
    text_column="cleaned_text",
    width=1200,
    height=600,
    max_words=150
):

    if text_column not in df.columns:
        df = prepare_text(df)

    texts = (
        df[text_column]
        .dropna()
        .astype(str)
    )

    text = " ".join(texts)

    if not text.strip():
        return None

    # Remove stopwords before passing text to WordCloud.
    filtered_words = [
        word
        for word in tokenize_text(text)
    ]

    if not filtered_words:
        return None

    wordcloud = WordCloud(
        width=width,
        height=height,
        background_color="white",
        stopwords=STOPWORDS,
        max_words=max_words,
        collocations=False
    )

    wordcloud.generate(" ".join(filtered_words))

    return wordcloud


# ============================================================
# 6. KEYWORDS BY CLASSIFICATION CATEGORY
# ============================================================

def get_keywords_by_category(
    df,
    dimension="product_module",
    label_mode="primary",
    top_n=15,
    min_reviews=10
):

    if dimension not in DIMENSIONS:
        raise ValueError(
            f"Unsupported dimension: {dimension}"
        )

    if label_mode not in ["primary", "all"]:
        raise ValueError(
            "label_mode must be 'primary' or 'all'."
        )

    working = prepare_text(df)

    column = f"{dimension}_{label_mode}"

    if column not in working.columns:
        raise ValueError(
            f"Missing classification column: {column}"
        )

    records = []

    for _, row in working.iterrows():

        if label_mode == "primary":

            value = row[column]

            labels = (
                [str(value).strip()]
                if pd.notna(value) and str(value).strip()
                else []
            )

        else:
            labels = parse_labels(row[column])

        for label in set(labels):

            records.append({
                "classification_id": row.get(
                    "classification_id", _
                ),
                "category": label,
                "cleaned_text": row["cleaned_text"]
            })

    if not records:
        return pd.DataFrame(
            columns=[
                "category",
                "keyword",
                "frequency",
                "review_count"
            ]
        )

    category_df = pd.DataFrame(records)

    results = []

    for category, group in category_df.groupby("category"):

        review_count = group["classification_id"].nunique()

        if review_count < min_reviews:
            continue

        keywords = get_top_keywords(
            group,
            top_n=top_n
        )

        for _, row in keywords.iterrows():

            results.append({
                "category": category,
                "keyword": row["keyword"],
                "frequency": row["frequency"],
                "review_count": review_count
            })

    return pd.DataFrame(results)


# ============================================================
# 7. TEXT ANALYTICS SUMMARY
# ============================================================

def get_text_analytics_summary(df):

    working = prepare_text(df)

    total_reviews = len(working)

    nonempty = working["cleaned_text"].str.strip().ne("")

    word_counts = (
        working["cleaned_text"]
        .str.split()
        .str.len()
    )

    vocabulary = set()

    for text in working["cleaned_text"]:
        vocabulary.update(tokenize_text(text))

    return {
        "total_reviews": total_reviews,
        "reviews_with_text": int(nonempty.sum()),
        "empty_reviews": int((~nonempty).sum()),
        "average_words_per_review": (
            round(float(word_counts.mean()), 2)
            if total_reviews else 0
        ),
        "unique_vocabulary": len(vocabulary)
    }
