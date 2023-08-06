FROM python:3.10

WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5678
EXPOSE 8000
EXPOSE 8001
EXPOSE 5672

CMD [ "python", "-u", "-m", "app" ]
