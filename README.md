Search Engine Project


This project consists of two parts:

Front-End: A basic search engine interface.
Back-End: A web crawler that generates an inverted index and a resolved inverted index.
Requirements
Before you start testing, make sure you have the following installed:

Python 3.x

Required Python libraries: bottle, requests, beautifulsoup4, urllib3

Testing the Front-End
Navigate to the front-end folder:
cd frontend

Run app.py

python3 app.py
Access the front-end in your browser: Open your browser and go to:
http://localhost:8081
You should now see the search engine interface, where you can input keywords to see search results.

Testing the Crawler (Back-End)

1. Start the Local HTML Test Server
Navigate to the test HTML files directory:

cd backend/test_html_files

Start a local server to serve the HTML files:

python3 -m http.server 8000

This will start a local server at http://localhost:8000, which serves the test HTML files.

3. Run the Crawler and Check the Inverted Index
Navigate back to the backend folder:

cd ../

Run the test.py script to crawl the test URLs:

python3 test.py

This script will crawl the URLs defined in urls.txt, generate an inverted index and a resolved inverted index, and display the output in the terminal.

