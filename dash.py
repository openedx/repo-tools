import time

from age.age import get_wall_data

from flask import Flask, send_from_directory


app = Flask(__name__)
app.debug = True

@app.route('/')
def hello():
    return 'Hello World!?'

@app.route('/boom')
def boom():
    1/0

@app.route('/age/write', methods=['GET', 'POST'])
def write_age():
    start = time.time()
    age_json = get_wall_data()
    end = time.time()
    with open("age/age.json", "w") as age_json_file:
        age_json_file.write(age_json)
        return "Wrote {} bytes in {:.1f}s".format(len(age_json), end - start)

@app.route('/age/<path:filename>')
def send_static(filename):
    return send_from_directory('age', filename)
