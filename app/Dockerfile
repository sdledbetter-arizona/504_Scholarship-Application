FROM python:3.9

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

COPY . /app

CMD ["python", "main.py"]