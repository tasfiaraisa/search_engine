from bottle import Bottle, template, static_file, request, redirect, response
import time

app = Bottle()

#Global dictionary
global_keywords = {}
keywords = None
top_keywords = {}
word_counts = {}


@app.route('/static/<filename>')
def serve_static(filename):
    return static_file(filename, root='./static')

@app.route('/', method=['GET'])
def home():
    response.set_header('Cache-Control', 'max-age= 0')
    global top_keywords
    #Check if the 'keywords' parameter is in the query
    if 'keywords' in request.query:
        #Get the search query from the form
        global keywords
        keywords = request.query.keywords

        global word_counts
        word_counts = {}
        #Split the keywords string into individual words and count occurrences
        word_list = keywords.lower().split()
        for word in word_list:
            if word in word_counts:
                word_counts[word] += 1
            else:
                word_counts[word] = 1

            #Update the global_keyword counts
            if word in global_keywords:
                global_keywords[word] += 1
            else:
                global_keywords[word] = 1

        #Sort the global_keywords by count and get the top 20
        top_keywords = dict(sorted(global_keywords.items(), key=lambda item: item[1], reverse=True)[:20])
        redirect('/search')
       
    #If it's a GET, just render the home template
    rendered_template = template('home', top_keywords=top_keywords)
    return rendered_template

@app.route('/search', method='GET')
def search():
    global keywords
    global word_counts
    #Render the result page, passing the keywords and word_counts
    return template('result', keywords = keywords, word_count=word_counts)

app.run(host='localhost', port=8083, debug=True)
