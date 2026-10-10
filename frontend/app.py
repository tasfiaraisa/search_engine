from bottle import Bottle, template, static_file, request, redirect, response
import bottle
#from bottle import mark_safe
from oauth2client.client import OAuth2WebServerFlow, flow_from_clientsecrets
from googleapiclient.errors import HttpError
from beaker.middleware import SessionMiddleware
import time
import httplib2
import traceback
import psycopg
from html import escape
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
bottle.TEMPLATE_PATH.insert(0, str(BASE_DIR / "views"))

# Initialize the Bottle app
app = Bottle()


# Session management configuration
session_opts = {
    'session.type': 'memory',
    'session.auto': True
}

@app.route('/static/<filename:path>')
def serve_static(filename):
    return static_file(filename, root=str(BASE_DIR / "static"))

# Search route - Fetch URLs based on PageRank scores
@app.route('/search', method='GET')
def search():
    keywords = request.query.get('keywords', '').strip().lower()

    try:
        page = max(1, int(request.query.get('page', 1)))
    except ValueError:
        page = 1

    results_per_page = 5
    offset = (page - 1) * results_per_page

    # Split the search query into individual words
    search_terms = keywords.split()

    if not search_terms:
        return template(
            'result',
            table_rows='',
            total_results=0,
            keywords=keywords,
            page=page,
            pages=0
        )

    # Match any search term in the inverted index.
    # Use PageRank to rank matching documents.
    search_query = """
        SELECT
            d.url,
            COALESCE(p.score, 0) AS pagerank_score,
            COUNT(DISTINCT l.word) AS matching_words
        FROM inverted_index i
        JOIN lexicon l ON i.word_id = l.id
        JOIN document_index d ON i.document_id = d.id
        LEFT JOIN pagerank p ON p.document_id = d.id
        WHERE l.word = ANY(%s)
          AND d.url <> ''
        GROUP BY d.id, d.url, p.score
        ORDER BY matching_words DESC, pagerank_score DESC
        LIMIT %s OFFSET %s
    """

    count_query = """
        SELECT COUNT(DISTINCT i.document_id)
        FROM inverted_index i
        JOIN lexicon l ON i.word_id = l.id
        JOIN document_index d ON i.document_id = d.id
        WHERE l.word = ANY(%s)
          AND d.url <> ''
    """

    with psycopg.connect(dbname="search_engine") as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                search_query,
                (search_terms, results_per_page, offset)
            )
            query_result = cursor.fetchall()

            cursor.execute(count_query, (search_terms,))
            total_results = cursor.fetchone()[0]

    pages = (total_results + results_per_page - 1) // results_per_page

    table_rows = ''

    for idx, (url, score, matching_words) in enumerate(query_result):
        rank = idx + 1 + offset

        safe_url = escape(url, quote=True)

        # Display a readable title based on the URL.
        from urllib.parse import urlparse, unquote

        parsed = urlparse(url)
        page_name = unquote(parsed.path.rstrip('/').split('/')[-1])

        if page_name:
            display_title = page_name.replace('_', ' ').replace('-', ' ')
        else:
            display_title = parsed.netloc

        safe_title = escape