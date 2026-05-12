# Imagem base oficial da AWS Lambda para Python 3.13
FROM public.ecr.aws/lambda/python:3.13

# Copiar e instalar dependências
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copiar código-fonte
COPY src/ ${LAMBDA_TASK_ROOT}/

# Handler padrão
CMD ["lambda_function.lambda_handler"]
