FROM python:3.10-slim
WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get -y install fluidsynth && pip install -r requirements.txt

COPY . .

WORKDIR ./application
CMD ["python", "-m" , "flask", "run", "--host=0.0.0.0"]