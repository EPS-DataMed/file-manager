import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os
import mimetypes
from typing import List

load_dotenv()

app = FastAPI()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'],
    region_name=os.environ['S3_REGION_NAME']
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

@app.put("/upload/")
async def upload_pdf_files(files: List[UploadFile] = File(...)):
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
                files_messages.append(f"The File '{uploaded_file.filename}' exceeds the size limit of '{MAX_FILE_SIZE_STRING}")
                if real_status_code != 500:
                    real_status_code = 400
                continue

            s3_client.put_object(
                Bucket=os.environ['S3_BUCKET_NAME'],
                Key=uploaded_file.filename,
                Body=contents
            )
            files_messages.append(f"The file '{uploaded_file.filename}' has been successfully uploaded")
        except ClientError as e:
            files_messages.append(f"Error while uploading the file '{uploaded_file.filename}' to AWS S3")
            real_status_code = 500
    
    if files_messages:
        return JSONResponse(content={"message": files_messages}, status_code=real_status_code)
    else:
        return JSONResponse(content={"message": "No files were uploaded"}, status_code=real_status_code)

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    try:
        # Verify if the file exists in the S3 bucket
        response = s3_client.head_object(
            Bucket=os.environ['S3_BUCKET_NAME'],
            Key=filename
        )

        s3_client.delete_object(
            Bucket=os.environ['S3_BUCKET_NAME'],
            Key=filename
        )

        return JSONResponse(content={"message": f"The file '{filename}' has been successfully deleted"}, status_code=200)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            raise HTTPException(status_code=404, detail=f"The file '{filename}' does not exist")
        else:
            raise HTTPException(status_code=500, detail=f"Error while deleting the file '{filename}' on AWS S3")

if __name__ == "__main__":
    uvicorn.run(
        "file_management:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )