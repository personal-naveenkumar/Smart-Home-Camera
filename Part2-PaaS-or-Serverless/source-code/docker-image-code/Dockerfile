FROM public.ecr.aws/lambda/python:3.8

COPY . ./
RUN chmod 777 install_requirements.sh
RUN ./install_requirements.sh

CMD ["lambda_file.lambda_handler"]