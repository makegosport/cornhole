FROM python:buster

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .
CMD [ "python", "-u", "./colourdetect_rt.py"]