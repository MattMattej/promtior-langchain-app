from flask import Flask, request, jsonify, render_template
from app import get_response, scrape_promtior
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    question = data['message']
    response = get_response(question)
    return jsonify({"reply": response})

@app.route('/api/context', methods=['POST'])
def context():
    context_docs = scrape_promtior()
    return jsonify({"context": context_docs})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
