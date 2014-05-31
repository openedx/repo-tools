from flask import Flask, send_from_directory

app = Flask(__name__)
app.debug = True

@app.route('/')
def hello():
    return 'Hello World!?'

@app.route('/boom')
def boom():
    1/0

@app.route('/f/<path:filename>')
def send_static(filename):
    return send_from_directory('.', filename)

@app.route('/write')
def write():
    with open("info.txt", "w") as info_txt:
        info_txt.write("Hello there info.txt!\n")
    return 'Done!'
