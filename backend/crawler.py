# Copyright (C) 2011 by Peter Goodman
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import urllib3
from urllib.parse import urlparse, urldefrag, urljoin
from urllib.request import urlopen
from bs4 import BeautifulSoup, Tag
from collections import defaultdict
import re
import requests
from database import get_connection
import numpy as np


def attr(elem, attr):
    """An html attribute from an html element. E.g. <a href="">, then
    attr(elem, "href") will get the href or an empty string."""
    try:
        return elem[attr]
    except:
        return ""


WORD_SEPARATORS = re.compile(r'\s|\n|\r|\t|[^a-zA-Z0-9\-_]')
timeout = 10

class crawler(object):
    """Represents 'Googlebot'. Populates a database by crawling and indexing
    a subset of the Internet.

    This crawler keeps track of font sizes and makes it simpler to manage word
    ids and document ids."""

    def __init__(self, db_conn, url_file):
        """Initialize the crawler with a connection to the database to populate
        and with the file containing the list of seed URLs to begin indexing."""
        self._url_queue = []
        self._doc_id_cache = {}
        self._word_id_cache = {}
        self.db_conn = db_conn
        self.cursor = self.db_conn.cursor()
        self.graph = defaultdict(list)
        self._create_tables()
        
         # Initialize the data structures
        self.lexicon = {}  
        self.document_index = {}  
        self.inverted_index = defaultdict(set)  # word_id -> set(doc_ids)
        self.visited = set()
        self.queued_urls = set()
        self.max_depth = 1

        # functions to call when entering and exiting specific tags
        self._enter = defaultdict(lambda *a, **ka: self._visit_ignore)
        self._exit = defaultdict(lambda *a, **ka: self._visit_ignore)

        # add a link to our graph, and indexing info to the related page
        self._enter['a'] = self._visit_a

        # record the currently indexed document's title an increase
        # the font size
        def visit_title(*args, **kargs):
            self._visit_title(*args, **kargs)
            self._increase_font_factor(7)(*args, **kargs)

        # increase the font size when we enter these tags
        self._enter['b'] = self._increase_font_factor(2)
        self._enter['strong'] = self._increase_font_factor(2)
        self._enter['i'] = self._increase_font_factor(1)
        self._enter['em'] = self._increase_font_factor(1)
        self._enter['h1'] = self._increase_font_factor(7)
        self._enter['h2'] = self._increase_font_factor(6)
        self._enter['h3'] = self._increase_font_factor(5)
        self._enter['h4'] = self._increase_font_factor(4)
        self._enter['h5'] = self._increase_font_factor(3)
        self._enter['title'] = visit_title

        # decrease the font size when we exit these tags
        self._exit['b'] = self._increase_font_factor(-2)
        self._exit['strong'] = self._increase_font_factor(-2)
        self._exit['i'] = self._increase_font_factor(-1)
        self._exit['em'] = self._increase_font_factor(-1)
        self._exit['h1'] = self._increase_font_factor(-7)
        self._exit['h2'] = self._increase_font_factor(-6)
        self._exit['h3'] = self._increase_font_factor(-5)
        self._exit['h4'] = self._increase_font_factor(-4)
        self._exit['h5'] = self._increase_font_factor(-3)
        self._exit['title'] = self._increase_font_factor(-7)

        # never go in and parse these tags
        self._ignored_tags = {'meta', 'script', 'link', 'meta', 'embed', 'iframe', 'frame', 'noscript', 'object', 'svg',
                              'canvas', 'applet', 'frameset', 'textarea', 'style', 'area', 'map', 'base', 'basefont',
                              'param'}

        # set of words to ignore
        self._ignored_words = {'', 'the', 'of', 'at', 'on', 'in', 'is', 'it', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h',
                               'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                               'and', 'or'}

        # TODO remove me in real version
        self._mock_next_doc_id = 1
        self._mock_next_word_id = 1

        # keep track of some info about the page we are currently parsing
        self._curr_depth = 0
        self._curr_url = ""
        self._curr_doc_id = 0
        self._font_size = 0
        self._curr_words = None

        # Get valid seed URLs into the queue
        try:
            with open(url_file, 'r') as f:
                for line in f:
                    url = line.strip()

                    # Skip empty lines and invalid URLs
                    if not url or not url.startswith(("http://", "https://")):
                        continue

                    fixed_url = self._fix_url(url, "")

                    # Avoid duplicate seed URLs
                    if fixed_url not in [item[0] for item in self._url_queue]:
                        self._url_queue.append((fixed_url, 0))
                        self.queued_urls.add(fixed_url)

        except IOError:
            print(f"Could not open URL file: {url_file}")

            
            
    def _create_tables(self):
        """Database tables are created by schema.sql."""
        pass
        
        
    
    def save_to_db(self):
        """Save crawled words, documents, and inverted index to PostgreSQL."""

        # Save words
        for word_id, word in self.lexicon.items():
            self.cursor.execute(
                """
                INSERT INTO lexicon (id, word)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (word_id, word)
            )

        # Save documents
        for doc_id, url in self.document_index.items():
            self.cursor.execute(
                """
                INSERT INTO document_index (id, url)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (doc_id, url)
            )

        # Save inverted index
        for word_id, doc_ids in self.inverted_index.items():
            for doc_id in doc_ids:
                self.cursor.execute(
                    """
                    INSERT INTO inverted_index (word_id, document_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (word_id, doc_id)
                )

        self.db_conn.commit()
        print("Crawler data saved to PostgreSQL!")
        
    def compute_and_store_pagerank(self):
        # Convert graph to links
        links = []
        for src, dsts in self.graph.items():
            for dst in dsts:
                links.append((src, dst))
        
        # Compute PageRank
        pagerank_scores = page_rank(links)

        # Store PageRank in the database
        store_pagerank_scores(self.db_conn, pagerank_scores)

        
        
    # TODO remove me in real version
    def _mock_insert_document(self, url):
        """A function that pretends to insert a url into a document db table
        and then returns that newly inserted document's id."""
        ret_id = self._mock_next_doc_id
        self.document_index[ret_id] = url  # Add the document ID -> URL mapping to the document index
        self._mock_next_doc_id += 1
        return ret_id

    # TODO remove me in real version
    def _mock_insert_word(self, word):
        """A function that pretends to inster a word into the lexicon db table
        and then returns that newly inserted word's id."""
        ret_id = self._mock_next_word_id
        self._mock_next_word_id += 1
        return ret_id

    def word_id(self, word):
        """Get or create a word ID in PostgreSQL."""

        if word in self._word_id_cache:
            return self._word_id_cache[word]

        self.cursor.execute(
            "SELECT id FROM lexicon WHERE word = %s",
            (word,)
        )
        result = self.cursor.fetchone()

        if result:
            word_id = result[0]
        else:
            self.cursor.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM lexicon"
            )
            word_id = self.cursor.fetchone()[0]

            self.cursor.execute(
                "INSERT INTO lexicon (id, word) VALUES (%s, %s)",
                (word_id, word)
            )

        self._word_id_cache[word] = word_id
        self.lexicon[word_id] = word
        return word_id

    def document_id(self, url):
        """Get or create a document ID in PostgreSQL."""

        if url in self._doc_id_cache:
            return self._doc_id_cache[url]

        self.cursor.execute(
            "SELECT id FROM document_index WHERE url = %s",
            (url,)
        )
        result = self.cursor.fetchone()

        if result:
            doc_id = result[0]
        else:
            self.cursor.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM document_index"
            )
            doc_id = self.cursor.fetchone()[0]

            self.cursor.execute(
                "INSERT INTO document_index (id, url) VALUES (%s, %s)",
                (doc_id, url)
            )

        self._doc_id_cache[url] = doc_id
        self.document_index[doc_id] = url
        return doc_id

    def _fix_url(self, curr_url, rel):
        """Given a url and either something relative to that url or another url,
        get a properly parsed url."""

        rel_l = rel.lower()
        if rel_l.startswith("http://") or rel_l.startswith("https://"):
            curr_url, rel = rel, ""

        # compute the new url based on import
        curr_url = urldefrag(curr_url)[0]
        parsed_url = urlparse(curr_url)
        return urljoin(parsed_url.geturl(), rel)

    def add_link(self, from_doc_id, to_doc_id):
        """Add a link into the database, or increase the number of links between
        two pages in the database."""
        # TODO

    def _visit_title(self, elem):
        """Called when visiting the <title> tag."""
        title_text = self._text_of(elem).strip()
        print("document title=" + repr(title_text))

        # TODO update document title for document id self._curr_doc_id

    def _visit_a(self, elem):
        """Process hyperlinks without adding duplicate URLs."""

        href = attr(elem, "href").strip()

        # Ignore empty links and non-web URLs
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            return

        dest_url = self._fix_url(self._curr_url, href)

        if not dest_url or dest_url == self._curr_url:
            return

        parsed = urlparse(dest_url)

        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return

        # Record the link for PageRank
        from_doc_id = self._curr_doc_id
        to_doc_id = self.document_id(dest_url)

        if to_doc_id not in self.graph[from_doc_id]:
            self.graph[from_doc_id].append(to_doc_id)

        # Only queue URLs within the crawl depth limit
        next_depth = self._curr_depth

        if (
            next_depth <= self.max_depth
            and dest_url not in self.queued_urls
        ):
            self._url_queue.append((dest_url, next_depth))
            self.queued_urls.add(dest_url)

    def _add_words_to_document(self):
        # TODO: knowing self._curr_doc_id and the list of all words and their
        #       font sizes (in self._curr_words), add all the words into the
        #       database for this document
        for word_id, font_size in self._curr_words:
            # Add the current document ID to the set of document IDs associated with this word_id
            self.inverted_index[word_id].add(self._curr_doc_id)
        print("    num words=" + str(len(self._curr_words)))

    def _increase_font_factor(self, factor):
        """Increade/decrease the current font size."""

        def increase_it(elem):
            self._font_size += factor

        return increase_it

    def _visit_ignore(self, elem):
        """Ignore visiting this type of tag"""
        pass

    def _add_text(self, elem):
        """Add some text to the document. This records word ids and word font sizes
        into the self._curr_words list for later processing."""
        words = WORD_SEPARATORS.split(elem.string.lower())
        for word in words:
            word = word.strip()
            if word in self._ignored_words:
                continue
            self._curr_words.append((self.word_id(word), self._font_size))

    def _text_of(self, elem):
        """Get the text inside some element without any tags."""
        if isinstance(elem, Tag):
            text = []
            for sub_elem in elem:
                text.append(self._text_of(sub_elem))

            return " ".join(text)
        else:
            return elem.string

    def _index_document(self, soup):
        """Traverse the document in depth-first order and call functions when entering
        and leaving tags. When we come accross some text, add it into the index. This
        handles ignoring tags that we have no business looking at."""

        class DummyTag(object):
            next = False
            name = ''

        class NextTag(object):
            def __init__(self, obj):
                self.next = obj

        tag = soup.html
        stack = [DummyTag(), soup.html]

        while tag and tag.next:
            tag = tag.next

            # html tag
            if isinstance(tag, Tag):

                if tag.parent != stack[-1]:
                    self._exit[stack[-1].name.lower()](stack[-1])
                    stack.pop()

                tag_name = tag.name.lower()

                # ignore this tag and everything in it
                if tag_name in self._ignored_tags:
                    if tag.nextSibling:
                        tag = NextTag(tag.nextSibling)
                    else:
                        self._exit[stack[-1].name.lower()](stack[-1])
                        stack.pop()
                        tag = NextTag(tag.parent.nextSibling)

                    continue

                # enter the tag
                self._enter[tag_name](tag)
                stack.append(tag)

            # text (text, cdata, comments, etc.)
            else:
                self._add_text(tag)
                
    def get_inverted_index(self):
        """Return the inverted index as a dictionary with word IDs as keys and document IDs as values."""
        return dict(self.inverted_index)
    
    def get_resolved_inverted_index(self):
        """Return a human-readable inverted index with words and URLs instead of word and document IDs."""
        resolved_index = {}
        for word_id, doc_ids in self.inverted_index.items():
            word = self.lexicon[word_id]  # Get the word from the word_id
            urls = {self.document_index[doc_id] for doc_id in doc_ids}  # Get the URLs from the doc_ids
            resolved_index[word] = urls
        return resolved_index

    def crawl(self, depth=2, timeout=3, max_pages = 50):
        """Crawl the web!"""
        self.max_depth = depth
        seen = set()
        pages_crawled = 0

        while len(self._url_queue):
            if pages_crawled >= max_pages:
                print(f"Reached crawl limit of {max_pages} pages.")
                break

            url, depth_ = self._url_queue.pop()
            
           
            if depth_ > depth:
                continue
            
            print(f"Crawling: {url}, Depth: {depth_}")
            
            doc_id = self.document_id(url)

            # we've already seen this document
            if doc_id in seen:
                continue

            seen.add(doc_id)  # mark this document as haven't been visited

            socket = None
            try:
                response = requests.get(url, timeout=timeout, verify=False)
                soup = BeautifulSoup(response.text, features="html.parser")

                self._curr_depth = depth_ + 1
                self._curr_url = url
                self._curr_doc_id = doc_id
                self._font_size = 0
                self._curr_words = []
                self._index_document(soup)
                self._add_words_to_document()
                pages_crawled += 1
                print("    url=" + repr(self._curr_url))


            except Exception as e:
                print(e)
                pass


def page_rank(links, num_iterations=20, initial_pr=1.0, damping_factor=0.85):

    # Initialize PageRank scores and link data structures
    page_rank = defaultdict(lambda: float(initial_pr))
    num_outgoing_links = defaultdict(float)
    incoming_link_sets = defaultdict(set)

    # Populate link data structures
    for from_id, to_id in links:
        num_outgoing_links[from_id] += 1.0
        incoming_link_sets[to_id].add(from_id)

    # Identify all unique nodes
    all_nodes = set(num_outgoing_links.keys()).union(set(incoming_link_sets.keys()))
    
    # Handle dangling nodes
    for node in all_nodes:
        if node not in num_outgoing_links:
            num_outgoing_links[node] = 0

    num_documents = len(all_nodes)
    if num_documents == 0:
        return {}

    lead = (1.0 - damping_factor) / num_documents

    for _ in range(num_iterations):
        new_page_rank = defaultdict(float)

        # Compute contributions from incoming links
        for node in all_nodes:
            tail = 0.0
            if node in incoming_link_sets:
                for incoming in incoming_link_sets[node]:
                    if num_outgoing_links[incoming] > 0:  # Avoid division by zero
                        tail += damping_factor * (page_rank[incoming] / num_outgoing_links[incoming])
                    else:
                        print(f"Warning: Dangling node {incoming} detected.")
            new_page_rank[node] = lead + tail

        # Redistribute PageRank from dangling nodes
        dangling_sum = sum(page_rank[node] for node in all_nodes if num_outgoing_links[node] == 0)
        dangling_contribution = damping_factor * (dangling_sum / num_documents)
        for node in all_nodes:
            new_page_rank[node] += dangling_contribution

        # Debugging output to detect anomalies
        print(f"Iteration completed. Dangling contribution: {dangling_contribution}")

        page_rank = new_page_rank

    return dict(page_rank)





def store_pagerank_scores(db_conn, pagerank_scores):
    """Save PageRank scores to PostgreSQL."""

    with db_conn.cursor() as cursor:
        for doc_id, score in pagerank_scores.items():
            cursor.execute(
                """
                INSERT INTO pagerank (document_id, score)
                VALUES (%s, %s)
                ON CONFLICT (document_id)
                DO UPDATE SET score = EXCLUDED.score
                """,
                (doc_id, float(score))
            )

    db_conn.commit()
    print("PageRank scores saved to PostgreSQL!")
  
    
if __name__ == "__main__":
    url_file = "url.txt"  # Path to file containing seed URLs
    depth = 1                   # Crawling depth
    timeout = 10                # Request timeout in seconds
    iterations = 20             # Number of iterations for PageRank computation

    # Connect to PostgreSQL
    db_conn = get_connection()

    try:
        # Initialize the crawler
        web_crawler = crawler(db_conn, url_file)
        
        # Start crawling
        print(f"Starting crawl with depth={depth}, timeout={timeout}s")
        web_crawler.crawl(depth=depth, timeout=timeout)
        
        # Save crawled data to the database
        print("Saving crawled data to d