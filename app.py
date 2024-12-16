import os
import json
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from langchain.schema.runnable import RunnableSequence
from langchain_openai import OpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile  # Para manejo de archivos temporales

# Cargar variables de entorno
load_dotenv()

# Configuración del modelo
llm = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), max_tokens=500)  # Respuestas más extensas

# Configuración del template del prompt
template = PromptTemplate(
    input_variables=["question", "context"],
    template="Pregunta: {question}\nContexto: {context}\nRespuesta:"
)

# Crear la cadena de procesamiento usando RunnableSequence
chain = RunnableSequence(template | llm)

# Crear el índice vectorial vacío
embeddings = OpenAIEmbeddings()
vector_store = None  # Se inicializa vacío

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
        # Guardar archivo temporalmente
        with NamedTemporaryFile(delete=True, suffix=".pdf") as temp_file:
            file.save(temp_file.name)

            # Procesar el archivo con PyPDFLoader
            loader = PyPDFLoader(temp_file.name)
            documents = loader.load()

            # Crear índice vectorial
            vector_store = FAISS.from_documents(documents, embeddings)

            print("PDF cargado y procesado con éxito.")  # Console log
            return jsonify({"message": "PDF cargado y procesado con éxito"})
    else:
        return jsonify({"error": "Por favor sube un archivo PDF válido"}), 400

@app.route('/api/chat', methods=['POST'])
def chat():
    """Ruta para manejar las preguntas del usuario"""
    global vector_store
    if vector_store is None:
        return jsonify({"error": "Primero sube un PDF para poder realizar preguntas"}), 400
    
    data = request.get_json()
    question = data.get('message', '')

    # Recuperar documentos relevantes
    context_docs = vector_store.similarity_search(question, k=2)
    context_list = [
        {"content": doc.page_content, "source": doc.metadata.get('source', 'PDF')}
        for doc in context_docs
    ]
    context_text = "\n\n".join([f"{doc['content']} (Fuente: {doc['source']})" for doc in context_list])
    
    # Generar la respuesta usando la cadena de procesamiento
    response = chain.invoke({"question": question, "context": context_text})

    # Verificar si el usuario solicitó respuesta en JSON
    if "json" in question.lower():
        try:
            structured_response = {
                "Contexto": context_list,  # Lista de documentos relevantes
                "Respuesta": response
            }
            return jsonify(structured_response), 200  # Devolver como JSON correctamente indentado
        except Exception as e:
            return jsonify({"error": f"No se pudo estructurar la respuesta como JSON: {str(e)}"}), 500

    # Respuesta estándar en formato texto
    print("Pregunta procesada con éxito.")  # Console log
    return jsonify({"reply": response})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
