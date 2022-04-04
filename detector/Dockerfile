FROM python:3

COPY requirements.txt requirements.txt
RUN apt update
RUN apt install -y ffmpeg libsm6 libxext6
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
CMD [ "python", "-u", "./colourdetect_mqtt.py"]