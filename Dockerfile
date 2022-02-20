FROM python:3.10-bullseye

WORKDIR /pfaditag-registration

# install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# add project
COPY . .

# define variables
ENV FLASK_APP=registration.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000
EXPOSE 5000

CMD ["flask", "run"]
