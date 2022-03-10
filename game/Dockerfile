FROM python:bullseye

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .
CMD [ "python", "-u", "./main.py", "docker"]