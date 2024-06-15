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

class Test(BaseModel):
    id: int
    user_id: int
    test_name: str
    url: str
    submission_date: datetime

    class Config:
        from_attributes = True

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
    file_info = []
    messages = []
    real_status_code = 200
    for uploaded_file in files:
        if not is_pdf(uploaded_file.filename):
            messages.append(f"The file '{uploaded_file.filename}' is not a PDF, only PDF files are allowed")
            if real_status_code != 500:
                real_status_code = 400
            continue

        existing_test = db.query(models.Test).filter_by(user_id=user_id, test_name=uploaded_file.filename).first()
        if existing_test:
            messages.append(f"A test with the name '{uploaded_file.filename}' already exists for user '{user_id}'")
            if real_status_code != 500:
                real_status_code = 400
            continue

        try:
            contents = await uploaded_file.read()

            if not file_size_within_bounds(contents):
                messages.append(f"The File '{uploaded_file.filename}' exceeds the size limit of '{MAX_FILE_SIZE_STRING}'")
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
            
            test = models.Test(
                user_id=user_id,
                test_name=uploaded_file.filename,
                url=url,
                submission_date=datetime.utcnow()
            )
            db.add(test)
            db.commit()
            db.refresh(test)

            messages.append(f"The file '{uploaded_file.filename}' has been successfully uploaded for user '{user_id}'")
            file_info.append({
                "user_id": test.user_id,
                "id": test.id,
                "url": test.url,
                "test_name": uploaded_file.filename,
                "submission_date": test.submission_date.isoformat()
            })
        except ClientError as e:
            messages.append(f"Error while uploading the file '{uploaded_file.filename}' to AWS S3 for user '{user_id}'")
            real_status_code = 500

    if real_status_code == 200:
        return JSONResponse(content={"status": 200, "message": "File(s) uploaded successfully!", "data": file_info}, status_code=200)
    else:
        return JSONResponse(content={"status": real_status_code, "message": messages, "data": file_info}, status_code=real_status_code)

@app.delete("/data/delete/{user_id}/{file_id}")
async def delete_file(user_id: int, file_id: int, db: db_dependency):

    filename = db.query(models.Test).filter_by(user_id=user_id, id=file_id).first().test_name
    if not filename:
        raise HTTPException(status_code=404, detail="File not found")
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

        test = db.query(models.Test).filter_by(user_id=user_id, id=file_id).first()
        if test:
            db.delete(test)
            db.commit()

        return JSONResponse(content={"status": 200, "message": f"The file '{filename}' for user '{user_id}' has been successfully deleted"}, status_code=200)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            raise HTTPException(status_code=404, detail=f"The file '{filename}' for user '{user_id}' does not exist on AWS S3")
        else:
            raise HTTPException(status_code=500, detail=f"Error while deleting the file '{filename}' for user '{user_id}' on AWS S3")

@app.get("/data/tests/{user_id}")
async def list_user_tests(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

    tests = db.query(models.Test).filter_by(user_id=user_id).all()
    test_data = []
    for test in tests:
        test_dict = Test.from_orm(test).dict()
        if 'submission_date' in test_dict and isinstance(test_dict['submission_date'], datetime):
            test_dict['submission_date'] = test_dict['submission_date'].isoformat()
        test_data.append(test_dict)

    return JSONResponse(content={"status": 200, "message": f"The following tests found for user with ID {user_id}", "data": test_data}, status_code=200)


if __name__ == "__main__":
    uvicorn.run(
        "file:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
