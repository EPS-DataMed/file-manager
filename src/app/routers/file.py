import os
from os.path import dirname, abspath
d = dirname(dirname(abspath(__file__)))
import sys
sys.path.append(d)

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
import boto3
from botocore.exceptions import ClientError
import mimetypes
from typing import List, Annotated
from pydantic import BaseModel
from datetime import datetime
import models
from database import SessionLocal
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Exame(BaseModel):
    id: int
    id_usuario: int
    nome_exame: str
    url: str
    data_submissao: datetime

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv('S3_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('S3_SECRET_ACCESS_KEY'),
    region_name=os.getenv('S3_REGION_NAME')
)

# Define the maximum file size permitted for uploads
KB = 1024
MB = 1024 * KB
MAX_FILE_SIZE = 200 * MB
MAX_FILE_SIZE_STRING = "200MB"

def is_pdf(filename: str) -> bool:
    mimetype, _ = mimetypes.guess_type(filename)
    return mimetype == 'application/pdf'

def file_size_within_bounds(contents) -> bool:
    size_in_bytes = len(contents)
    return size_in_bytes <= MAX_FILE_SIZE

@app.post("/data/upload/{user_id}")
async def upload_pdf_files(user_id: int, db: db_dependency, files: List[UploadFile] = File(...)):
    files_messages = []
    real_status_code = 200
    for uploaded_file in files:
        if not is_pdf(uploaded_file.filename):
            files_messages.append(f"The file '{uploaded_file.filename}' is not a PDF, only PDF files are allowed")
            if real_status_code != 500:
                real_status_code = 400
            continue

        try:
            contents = await uploaded_file.read()

            if not file_size_within_bounds(contents):
                files_messages.append(f"The File '{uploaded_file.filename}' exceeds the size limit of '{MAX_FILE_SIZE_STRING}'")
                if real_status_code != 500:
                    real_status_code = 400
                continue
            
            s3_key = f"{user_id}/{uploaded_file.filename}"

            s3_client.put_object(
                Bucket=os.getenv('S3_BUCKET_NAME'),
                Key=s3_key,
                Body=contents
            )

            url = s3_client.generate_presigned_url(
                'get_object', 
                Params={'Bucket': os.getenv('S3_BUCKET_NAME'),
                'Key': s3_key}
            )
            
            exame = models.Exame(
                id_usuario=user_id,
                nome_exame=uploaded_file.filename,
                url=url,
                data_submissao=datetime.utcnow()
            )
            db.add(exame)
            db.commit()
            db.refresh(exame)

            files_messages.append(f"The file '{uploaded_file.filename}' has been successfully uploaded for user '{user_id}'")
        except ClientError as e:
            files_messages.append(f"Error while uploading the file '{uploaded_file.filename}' to AWS S3 for user '{user_id}'")
            real_status_code = 500
    if files_messages:
        return JSONResponse(content={"message": files_messages}, status_code=real_status_code)
    else:
        return JSONResponse(content={"message": "No files were uploaded"}, status_code=400)

@app.delete("/data/delete/{user_id}/{filename}")
async def delete_file(user_id: int, filename: str, db: db_dependency):
    try:
        s3_key = f"{user_id}/{filename}"

        # Verify if the file exists in the S3 bucket
        s3_client.head_object(
            Bucket=os.getenv('S3_BUCKET_NAME'),
            Key=s3_key
        )

        s3_client.delete_object(
            Bucket=os.getenv('S3_BUCKET_NAME'),
            Key=s3_key
        )

        exame = db.query(models.Exame).filter_by(id_usuario=user_id, nome_exame=filename).first()
        if exame:
            db.delete(exame)
            db.commit()

        return JSONResponse(content={"message": f"The file '{filename}' for user '{user_id}' has been successfully deleted"}, status_code=200)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            raise HTTPException(status_code=404, detail=f"The file '{filename}' for user '{user_id}' does not exist")
        else:
            raise HTTPException(status_code=500, detail=f"Error while deleting the file '{filename}' for user '{user_id}' on AWS S3")

@app.get("/data/download/{user_id}")
async def download_files(user_id: int, filenames: List[str] = Query(...)):
    files_messages = []
    real_status_code = 200
    
    for filename in filenames:
        s3_key = f"{user_id}/{filename}"
        try:
            # Verify if the file exists in the S3 bucket
            s3_client.head_object(
                Bucket=os.getenv('S3_BUCKET_NAME'),
                Key=s3_key
            )

            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': os.getenv('S3_BUCKET_NAME'), 'Key': s3_key},
                # URL expiration time in seconds
                ExpiresIn=3600  
            )
            files_messages.append({
                "filename": filename,
                "url": url
            })
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                files_messages.append(f"The file '{filename}' for user '{user_id}' does not exist")
                if real_status_code != 500:
                    real_status_code = 404
            else:
                files_messages.append(f"Error while generating download URL for the file '{filename}' for user '{user_id}' from AWS S3")
                real_status_code = 500

    return JSONResponse(content={"message": files_messages}, status_code=real_status_code)

@app.get("/data/exames/{user_id}")
async def list_user_exames(user_id: int, db: Session = Depends(get_db)):
    exames = db.query(models.Exame).filter_by(id_usuario=user_id).all()
    if not exames:
        raise HTTPException(status_code=404, detail=f"No exames found for user with ID {user_id}")
    return exames

if __name__ == "__main__":
    uvicorn.run(
        "file:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
    )
