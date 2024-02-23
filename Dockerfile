FROM python:3.12

RUN mkdir /code
WORKDIR /code

COPY requirements.txt ./

RUN pip install -U pip
RUN pip install -r requirements.txt

COPY .env scrapy.cfg ./

COPY main main/
