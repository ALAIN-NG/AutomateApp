# Utilise une image Python officielle
FROM python:3.12-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers
COPY . /app/

# Installer les dépendances
RUN pip install --upgrade pip \
    && pip install django gunicorn

# Port utilisé par Render
EXPOSE 8000

# Commande de lancement
CMD ["gunicorn", "TP_INF342.wsgi:application", "--bind", "0.0.0.0:8000"]
