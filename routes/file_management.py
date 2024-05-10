from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os
import mimetypes

load_dotenv()

app = FastAPI()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'],
    region_name=os.environ['S3_REGION_NAME']
)

def is_pdf(filename: str) -> bool:
    mimetype, _ = mimetypes.guess_type(filename)
    return mimetype == 'application/pdf'

@app.post("/upload/")
async def upload_files(files: UploadFile = File(...)):
    if not is_pdf(files.filename):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        contents = await files.read()

        s3_client.put_object(
            Bucket=os.environ['S3_BUCKET_NAME'],
            Key=files.filename,
            Body=contents
        )

        OBJECT_KEY = files.filename
        print(OBJECT_KEY)
        print('OBJECT_KEY')
        file_url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': os.environ['S3_BUCKET_NAME'], 'Key': OBJECT_KEY},
            ExpiresIn=1800
        )

        return JSONResponse(content={"file_url": file_url}, status_code=200)
    except ClientError as e:
        raise HTTPException(status_code=500, detail="Error while uploading the file to AWS S3")

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    try:
        s3_client.delete_object(
            Bucket=os.environ['S3_BUCKET_NAME'],
            Key=filename
        )
        return {"message": f"The file '{filename}' has been successfully deleted"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail="Error while deleting the file on AWS S3")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)