import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "carlosalberto-media")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")  # URL pública dinámica de tu bucket en R2

def get_r2_client():
    """Retorna un cliente de S3 adaptado automáticamente al entorno."""
    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
        raise ValueError("Las credenciales de Cloudflare R2 no están configuradas en este entorno.")
        
    session = boto3.session.Session()
    client = session.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )
    return client

def upload_file_to_r2(file_obj, filename: str, content_type: str) -> str:
    """Sube un archivo a Cloudflare R2 y retorna la URL pública completa o la clave."""
    client = get_r2_client()
    try:
        client.upload_fileobj(
            file_obj,
            R2_BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": content_type}
        )
        
        # Si R2_PUBLIC_URL está definida, retorna la URL pública completa lista para el navegador
        if R2_PUBLIC_URL:
            return f"{R2_PUBLIC_URL.rstrip('/')}/{filename}"
        return filename
    except Exception as e:
        print(f"Error al subir archivo a R2: {e}")
        raise e