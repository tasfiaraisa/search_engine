
import sqlite3

def test_database(db_name="pagerank.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Query lexicon
    print("Lexicon:")
    cursor.execute("SELECT * FROM lexicon")
    for row in cursor.fetchall():
        print(row)

    # Query document_index
    print("\nDocument Index:")
    cursor.execute("SELECT * FROM document_index")
    for row in cursor.fetchall():
        print(row)

    # Query inverted_index
    print("\nInverted Index:")
    cursor.execute("SELECT * FROM inverted_index")
    for row in cursor.fetchall():
        print(row)

    # Query pagerank
    print("\nPageRank Scores:")
    cursor.execute("SELECT * FROM pagerank")
    for row in cursor.fetchall():
        print(row)

    # Print database schema
    print("\n--- DATABASE SCHEMA --