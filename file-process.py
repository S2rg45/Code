import os
import shutil
import boto3
from botocore.exceptions import NoCredentialsError

# Directorio donde están los archivos
source_dir = 'file-process/'

aws_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")

# Nombre del bucket de S3
bucket_name = 'process-etl-glue'

# Crear una sesión de boto3
s3 = boto3.client('s3')

# Obtener la lista de archivos en el directorio
files = os.listdir(source_dir)

for file in files:
    # Obtenemos el nombre base sin la extensión
    base_name, ext = os.path.splitext(file)

    # Crear el nombre del directorio
    target_dir = os.path.join(source_dir, base_name)

    # Crear la carpeta si no existe
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Ruta completa del archivo de origen
    source_file = os.path.join(source_dir, file)

    # Ruta completa del archivo en la carpeta de destino
    target_file = os.path.join(target_dir, file)

    # Mover el archivo a la carpeta correspondiente
    shutil.move(source_file, target_file)

    # Subir la carpeta completa a S3
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            s3_key = os.path.relpath(file_path, source_dir)  # Relativo a la carpeta base

            try:
                # Subir el archivo a S3
                s3.upload_file(file_path, bucket_name, s3_key)
                print(f"Archivo {file_path} subido exitosamente a s3://{bucket_name}/{s3_key}")

            except FileNotFoundError:
                print(f"El archivo {file_path} no existe.")
            except NoCredentialsError:
                print("Credenciales no disponibles para AWS.")

print("Proceso completado.")