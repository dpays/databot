FROM python:3.6
ENV PIPENV_VENV_IN_PROJECT=1
RUN pip install pipenv
WORKDIR /dpaybot
ADD Pipfile Pipfile.lock /dpaybot/
RUN pipenv install
ADD . /dpaybot/
ENTRYPOINT ["pipenv", "run", "python", "-m", "dpaybot"]
