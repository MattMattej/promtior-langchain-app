import os
import json
from flask import Flask, request, jsonify, render_template, make_response
from werkzeug.utils import secure_filename
from langchain.schema.runnable import RunnableSequence
from langchain_openai import OpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile

# Cargar variables de entorno
load_dotenv()

# Configuración del modelo
llm = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    max_tokens=1000,
    temperature=0.1
)

# Configuración del template del prompt (incluyendo System Prompt)
system_prompt = (
    "Eres un asistente especializado en documentación bancaria de 'Bantotal', trabajando para 'Simplificado'. "
    "Responde basándote en los documentos PDF proporcionados."
)
template = PromptTemplate(
    input_variables=["question", "context"],
    template=f"{system_prompt}\n\nPregunta: {{question}}\nContexto: {{context}}\nRespuesta:"
)

# Crear la cadena de procesamiento usando RunnableSequence
chain = RunnableSequence(template | llm)

# Crear el índice vectorial vacío
embeddings = OpenAIEmbeddings()
vector_store = None

# Inicializar la app Flask
app = Flask(__name__)

@app.route('/')
def index():
    """Ruta principal para servir el archivo HTML"""
    return render_template('chat.html')

@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """Ruta para cargar y procesar un archivo PDF"""
    global vector_store
    file = request.files['file']
    if file and file.filename.endswith('.pdf'):
        try:
            with NamedTemporaryFile(delete=True, suffix=".pdf") as temp_file:
                file.save(temp_file.name)

                # Procesar el archivo con PyPDFLoader
                loader = PyPDFLoader(temp_file.name)
                documents = loader.load()

                # Crear índice vectorial
                vector_store = FAISS.from_documents(documents, embeddings)

                return jsonify({"message": "PDF cargado y procesado con éxito"})
        except Exception as e:
            return jsonify({"error": f"Ocurrió un error al procesar el PDF: {str(e)}"}), 500
    else:
        return jsonify({"error": "Por favor sube un archivo PDF válido"}), 400

@app.route('/api/chat', methods=['POST'])
def chat():
    """Ruta para manejar las preguntas del usuario"""
    global vector_store
    if vector_store is None:
        return jsonify({"error": "Primero sube un PDF para poder realizar preguntas"}), 400

    data = request.get_json()
    if not data or "message" not in data or not data["message"].strip():
        return jsonify({"error": "Por favor, proporcione un mensaje válido."}), 400

    question = data["message"].strip()

    try:
        context_docs = vector_store.similarity_search(question, k=2)
        context_list = [
            {"content": doc.page_content, "source": doc.metadata.get('source', 'PDF')}
            for doc in context_docs
        ]
        context_text = "\n\n".join([f"{doc['content']} (Fuente: {doc['source']})" for doc in context_list])

        response = chain.invoke({"question": question, "context": context_text})

        # Verificar si el usuario solicitó respuesta en JSON
        if any(keyword in question.lower() for keyword in ["json", ".json"]):
            structured_response = {
                "Contexto": context_list,
                "Respuesta": response
            }
            return jsonify(structured_response), 200

        return jsonify({"reply": response})
    except Exception as e:
        return jsonify({"error": f"Ocurrió un error al procesar la solicitud: {str(e)}"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    response = {
        "error": str(e),
        "message": "Ha ocurrido un error en el servidor. Por favor, intente nuevamente."
    }
    return make_response(jsonify(response), 500)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
