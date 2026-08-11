from flask import Flask, render_template_string, request
import ollama
import PyPDF2
import json
import os

app = Flask(__name__)
HISTORY_FILE = "chat_history.json"
PDF_FILE = "pdf_data.txt"

# Load history from file if exists
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)

def load_pdf():
    if os.path.exists(PDF_FILE):
        with open(PDF_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def save_pdf(text):
    with open(PDF_FILE, "w", encoding="utf-8") as f:
        f.write(text)

chat_history = load_history()
pdf_text = load_pdf()

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>My AI Assistant 🤖</title>
    <style>
        :root {
            --bg: #0f0f0f;
            --box: #1e1e1e;
            --text: white;
            --user: #25D366;
            --bot: #2a2a2a;
            --input: #2a2a2a;
        }
        body.light {
            --bg: #f0f2f5;
            --box: white;
            --text: #111;
            --user: #25D366;
            --bot: #e5e5ea;
            --input: #f0f2f5;
        }
        body { font-family: 'Segoe UI'; background: var(--bg); color: var(--text); margin: 0; padding: 20px; transition: 0.3s; }
        .chat-box { background: var(--box); padding: 20px; border-radius: 15px; max-width: 900px; margin: auto; height: 90vh; display: flex; flex-direction: column; }
        .header { display: flex; justify-content: space-between; align-items: center; }
        h2 { color: #25D366; margin: 0; }
        .btns { display: flex; gap: 10px; }
        .toggle-btn, .clear-btn { padding: 8px 15px; background: var(--user); color: black; border: none; border-radius: 20px; font-weight: bold; cursor: pointer; }
        .clear-btn { background: #ff3b30; }
        .pdf-info { background: var(--bot); padding: 10px; border-radius: 10px; text-align: center; margin: 10px 0; }
        .messages { flex: 1; overflow-y: auto; padding: 10px; }
        .msg { margin: 10px 0; padding: 10px 15px; border-radius: 18px; max-width: 75%; word-wrap: break-word; }
        .user { background: var(--user); color: black; margin-left: auto; text-align: right; }
        .bot { background: var(--bot); margin-right: auto; }
        form { display: flex; gap: 10px; margin-top: 10px; }
        input[type=text] { flex: 1; padding: 12px; border: none; border-radius: 25px; background: var(--input); color: var(--text); }
        input[type=file] { color: var(--text); }
        button { padding: 12px 20px; background: var(--user); color: black; border: none; border-radius: 25px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body class="dark">
    <div class="chat-box">
        <div class="header">
            <h2>🤖 My AI Assistant</h2>
            <div class="btns">
                <button type="button" class="clear-btn" onclick="clearHistory()">🗑️ Clear</button>
                <button type="button" class="toggle-btn" onclick="toggleTheme()">🌙/☀️</button>
            </div>
        </div>
        
        {% if pdf_loaded %}
        <div class="pdf-info">✅ PDF Loaded: You can ask questions about the PDF</div>
        {% endif %}
        
        <div class="messages" id="messages">
            {% for role, msg in history %}
                <div class="msg {{role}}"><b>{{'You' if role=='user' else 'AI'}}:</b> {{msg}}</div>
            {% endfor %}
        </div>
        
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="pdf" accept=".pdf">
            <input type="text" name="msg" placeholder="Ask anything..." autocomplete="off">
            <button>Send</button>
        </form>
    </div>

<script>
function toggleTheme() {
    document.body.classList.toggle('light');
    localStorage.setItem('theme', document.body.classList.contains('light') ? 'light' : 'dark');
}
if(localStorage.getItem('theme') === 'light') {
    document.body.classList.add('light');
}
document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;

function clearHistory() {
    if(confirm("Are you sure you want to delete all chat history?")) {
        fetch("/clear", {method: "POST"}).then(() => location.reload());
    }
}
</script>
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def home():
    global chat_history, pdf_text
    pdf_loaded = bool(pdf_text)

    if request.method == "POST":
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file.filename != '':
                pdf_reader = PyPDF2.PdfReader(file)
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() + "\n"
                save_pdf(pdf_text)
                chat_history.append(("bot", "PDF uploaded! Now you can ask questions about it 😎"))
                save_history(chat_history)
        
        user_msg = request.form.get("msg")
        if user_msg:
            chat_history.append(("user", user_msg))
            
            if pdf_text:
                full_prompt = f"Here is the PDF data: {pdf_text[:4000]}\n\nQuestion: {user_msg}\nAnswer based on the PDF."
            else:
                full_prompt = user_msg
            
            res = ollama.chat(model="llama3.1:8b", messages=[{"role": "user", "content": full_prompt}])
            bot_msg = res['message']['content']
            chat_history.append(("bot", bot_msg))
            save_history(chat_history)
        
    return render_template_string(HTML, history=chat_history, pdf_loaded=pdf_loaded)

@app.route("/clear", methods=["POST"])
def clear():
    global chat_history, pdf_text
    chat_history = []
    pdf_text = ""
    if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
    if os.path.exists(PDF_FILE): os.remove(PDF_FILE)
    return "ok"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")