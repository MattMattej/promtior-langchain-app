# Usa una imagen base de Python slim para reducir el uso de memoria
FROM python:3.9-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo requirements.txt en el directorio de trabajo
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el contenido de la aplicación en el directorio de trabajo
COPY . .

# Expone el puerto en el que la aplicación se ejecutará
EXPOSE 5000

# Comando para ejecutar la aplicación usando gunicorn con menor número de workers
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "server:app"]
