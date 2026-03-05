from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>AI Email Assistant</h1>
    <form action="/generate">
        <button type="submit">Generate Reply for Latest Email</button>
    </form>
    """

@app.route("/generate")
def generate():
    return "<h2>Generating reply...</h2>"

if __name__ == "__main__":
    app.run(debug=True)