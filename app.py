import os
import requests
from bs4 import BeautifulSoup
from langchain.chains import RunnableSequence
from langchain_openai import OpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import re

# Cargar variables de entorno
load_dotenv()

# Configuración del modelo
llm = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Configuración del template del prompt
template = PromptTemplate(input_variables=["question", "context"], 
                          template="Pregunta: {question}\nContexto: {context}\nRespuesta:")

# Crear la cadena de LLM usando RunnableSequence
chain = template | llm

# Documentos manuales
manual_documents = [
    Document(page_content="Promtior is an epic AI gen consultant", metadata={"source": "manual"}),
    Document(page_content="Promtior was founded in 2021.", metadata={"source": "manual"})
]

# Scraping de la web y creación de documentos automatizados
def scrape_promtior():
    urls = [
        "https://promtior.ai/",
        "https://www.promtior.ai/"
    ]
    content = []
    for url in urls:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Excluir elementos de navegación y otros no relevantes
        for nav in soup.find_all(['nav', 'header', 'footer', 'script', 'style']):
            nav.decompose()
        
        # Extraer contenido relevante
        for p in soup.find_all(['p', 'div', 'article', 'section']):
            text = p.get_text(strip=True)
            if text and len(text.split()) > 5:  # Filtrar texto corto y menos relevante
                content.append(text)
    
    full_content = " ".join(content)
    full_content = re.sub(r'\s+', ' ', full_content)  # Eliminar espacios redundantes
    return full_content

scraped_content = scrape_promtior()

# Crear documentos con el contenido scrapeado
scraped_documents = []
for paragraph in scraped_content.split(". "):
    if paragraph.strip() and len(paragraph.split()) > 10:  # Filtrar párrafos muy cortos
        scraped_documents.append(Document(page_content=paragraph.strip(), metadata={"source": "https://promtior.ai"}))

# Combinar documentos manuales y scrapeados
all_documents = manual_documents + scraped_documents

# Crear el índice vectorial de documentos usando FAISS
embeddings = OpenAIEmbeddings()
vector_store = FAISS.from_documents(all_documents, embeddings)

def get_response(question):
    # Recuperar documentos relevantes
    context_docs = vector_store.similarity_search(question, k=2)
    context = "\n\n".join([f"{doc.page_content} (Fuente: {doc.metadata['source']})" for doc in context_docs])
    
    # Generar la respuesta usando la cadena de LLM
    response = chain.invoke({"question": question, "context": context})
    return response

if __name__ == "__main__":
    question = input("Haz una pregunta: ")
    print(get_response(question))
