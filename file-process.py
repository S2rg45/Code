import os
import shutil
import boto3
import pytz
import datetime
import logging
from botocore.exceptions import NoCredentialsError


class UpFiles():
    def __init__(self, source_dir, bucket_name, dynamo_table):
        self.source_dir = source_dir
        self.bucket_name = bucket_name
        self.dynamo_table = dynamo_table
        self.aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
       
        self.s3_session = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.table = self.dynamodb.Table(self.dynamo_table)
    

    def move_and_upload_files(self):
        files = os.listdir(self.source_dir)
        for file in files:
            # Obtenemos el nombre base sin la extensión
            base_name, ext = os.path.splitext(file)
            # Crear el nombre del directorio
            target_dir = os.path.join(self.source_dir, base_name)
            # Crear la carpeta si no existe
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            # Ruta completa del archivo de origen
            source_file = os.path.join(self.source_dir, file)
            # Ruta completa del archivo en la carpeta de destino
            target_file = os.path.join(target_dir, file)
            # Mover el archivo a la carpeta correspondiente
            shutil.move(source_file, target_file)
            # Determinar si es una carpeta de "procesos" o "variables"
            if base_name.startswith("process-"):
                s3_folder = "procesos"
            elif base_name.startswith("variable-"):
                s3_folder = "variables"
            else:
                logging.info(f"El archivo {file} no pertenece a 'process-' o 'variable-', omitiendo...")
                continue
            # Subir la carpeta completa a S3
            for root, dirs, files in os.walk(target_dir):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    s3_key = os.path.join(s3_folder, os.path.relpath(file_path, self.source_dir))  # Relativo a la carpeta base
                    try:
                        # Validate if the folder already exists
                        if not self.check_if_folder_exists_in_s3(base_name, s3_folder):
                            # Crear el archivo en S3
                            self.s3_session.upload_file(file_path, self.bucket_name, s3_key)
                            # setear s3_key para utilizar el workflow
                            self.path_create_infra(base_name, s3_key)
                            logging.info(f"Archivo {file_path} subido exitosamente a s3://{self.bucket_name}/{s3_key}")
                            self.register_file_dynamodb(base_name, s3_key, is_new=True)
                            status="created"
                        else:
                            # Actualizar el archivo en S3
                            self.s3_session.upload_file(file_path, self.bucket_name, s3_key)
                            # setear s3_key para utilizar el workflow
                            self.path_create_infra(base_name, s3_key)
                            logging.info(f"Archivo {file_path} actualizado exitosamente en s3://{self.bucket_name}/{s3_key}")
                            # Actualizar en DynamoDB
                            self.register_file_dynamodb(base_name, s3_key, is_new=False)
                            status="update"
                    except FileNotFoundError:
                        logging.info(f"El archivo {file_path} no existe.")
                    except NoCredentialsError:
                        logging.info("Credenciales no disponibles para AWS.")
        self.set_output("status", status) 
        logging.info("--------------------------------")
        logging.info("Proceso completado.")
        logging.info("--------------------------------")

    
    def check_if_folder_exists_in_s3(self, folder_name, s3_folder):
        # Verifica si la carpeta existe en S3 usando list_objects_v2
        response = self.s3_session.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=s3_folder+'/'+folder_name+'/'  # Comprobar si hay objetos en la "carpeta"
        )
        # Si existen objetos bajo el prefijo, la carpeta existe
        return 'Contents' in response
    

    def path_create_infra(self,name_folder ,s3_key):
        if "variable" in s3_key:
            print(f"{name_folder}={s3_key}")


    def set_output(self, output_name, value):
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as variable:
                variable.write(f"{output_name}={value}")

    
    def register_file_dynamodb(self, folder_name, s3_key, is_new):
        guatemala_timezone = pytz.timezone('America/Guatemala')
        current_time_guatemala = datetime.datetime.now(guatemala_timezone)
        formatted_time = current_time_guatemala.strftime('%Y-%m-%d %H:%M:%S')
        status_flag = "created" if is_new else "update"
        try:
            if status_flag == "created":
                self.table.put_item(
                    Item={
                        "process-files": folder_name,
                        "S3_key":s3_key,
                        "CreationDate": formatted_time,
                        "Status": status_flag  
                    }
                )
                logging.info(f"Carpeta '{folder_name}', registrada correctamente con fecha {formatted_time}")
            else: 
                self.table.update_item(
                    Key={'process-files': folder_name},
                    UpdateExpression="SET S3_key = :S3_key, UpdateDate = :UpdateDate, #Status = :Status",
                    ExpressionAttributeValues={
                        ':S3_key': s3_key,
                        ':UpdateDate': formatted_time,
                        ':Status': status_flag
                    },
                    ExpressionAttributeNames={
                        '#Status': 'Status'  # Usamos un alias para evitar el conflicto con la palabra reservada
                    }
                )
                logging.info(f"Carpeta '{folder_name}',se actualizo correctamente con fecha {formatted_time}")
        except Exception as e:
            logging.info(f"Error al registrar en DynamoDB: {str(e)}")


if __name__ == "__main__":
    logging.info("--------------------------------")
    logging.info("Proceso iniciado")
    logging.info("--------------------------------")

    # Directorio donde están los archivos
    source_dir = 'file-process/'
    # Nombre del bucket de S3
    bucket_name = os.getenv("BUCKET_NAME_PROCESS") #'process-etl-glue-prod'
    # Nombre de la Tabla en DynamoDB
    dynamodb_table = os.getenv("DYNAMO_TABLE") #'state-files-process'
    region_name = os.getenv("AWS_REGION") #'us-east-2'
    uploader = UpFiles(source_dir, bucket_name, dynamodb_table)
    uploader.move_and_upload_files()
