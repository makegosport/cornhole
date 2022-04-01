FROM python:3

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
CMD [ "python", "-u", "./colourdetect_mqtt.py"]