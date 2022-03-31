FROM python:buster

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN apt-get update
RUN apt-get install -y python3-opencv python-numpy
COPY . .
CMD [ "python", "-u", "./colourdetect_rt.py"]