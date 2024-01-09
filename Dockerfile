# base image
FROM python:3.8-alpine

# setup environment variable
ENV DockerHOME=/app/

# set work directory
RUN mkdir -p $DockerHOME

# where your code lives
WORKDIR $DockerHOME

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk add --update --no-cache --virtual .tmp-build-deps \
    gcc libc-dev linux-headers postgresql-dev \
    && apk add libffi-dev

# install dependencies
RUN pip install --upgrade pip

# copy whole project to your docker home directory. 
COPY . $DockerHOME

# run this command to install all dependencies
RUN pip install -r requirements.txt
