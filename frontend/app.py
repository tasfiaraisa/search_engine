from bottle import Bottle, template, static_file

app = Bottle()

# Serve all static files (CSS, images, etc.)
@app.route('/static/<filename>')
def serve_static(filename):
    return static_file(filename, root='./static')

@app.route('/')
def home():
    return template('home')


app.run(host='localhost', port=8080, debug=True)
