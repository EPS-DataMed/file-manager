import os
from os.path import dirname, abspath
d = dirname(dirname(abspath(__file__)))
import sys
sys.path.append(d)

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from app.routers.file import app, MAX_FILE_SIZE_STRING, MAX_FILE_SIZE, MB
from botocore.exceptions import ClientError

@pytest.fixture
def client():
    return TestClient(app)

def test_upload_pdf_file(client):
    pdf_filename = "python_test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response = client.put("/upload/", files=file)
    assert response.status_code == 200
    assert response.json() == {'message': [f"The file '{pdf_filename}' has been successfully uploaded"]}

def test_upload_multiple_pdf_files(client):
    pdf_files = [
        ("python_test_file1.pdf", b"dummy pdf content 1"),
        ("python_test_file2.pdf", b"dummy pdf content 2"),
        ("python_test_file3.pdf", b"dummy pdf content 3")
    ]
    files = [("files", (name, content, "application/pdf")) for name, content in pdf_files]

    response = client.put("/upload/", files=files)
    assert response.status_code == 200
    uploaded_files = [f"The file '{name}' has been successfully uploaded" for name, _ in pdf_files]
    assert response.json() == {'message': uploaded_files}

def test_upload_non_pdf_file(client):
    non_pdf_filename = "python_test_file.txt"
    non_pdf_content = b"dummy text content"
    file = {"files": (non_pdf_filename, non_pdf_content, "text/plain")}

    response = client.put("/upload/", files=file)
    assert response.status_code == 400
    assert response.json() == {'message': [ f"The file '{non_pdf_filename}' is not a PDF, only PDF files are allowed"]}
   
def test_upload_large_pdf_file(client):
    large_filename = "python_test_large_file.pdf"
    large_file_size = MAX_FILE_SIZE + MB
    large_file_content = BytesIO(os.urandom(large_file_size))
    file = {"files": (large_filename, large_file_content, "application/pdf")}

    response = client.put("/upload/", files=file)
    assert response.status_code == 400
    assert response.json() == {'message': [ f"The File '{large_filename}' exceeds the size limit of '{MAX_FILE_SIZE_STRING}"]}

def test_upload_pdf_files_aws_exception(client, monkeypatch):
    def mock_put_object(Bucket, Key, Body):
        raise ClientError({"Error": {"Code": "MockException", "Message": "Simulated AWS S3 Error"}}, "put_object")
    
    monkeypatch.setattr("app.routers.file.s3_client.put_object", mock_put_object)
    
    pdf_filename = "python_test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response = client.put("/upload/", files=file)    
    assert response.status_code == 500
    assert response.json() == {'message': [f"Error while uploading the file '{pdf_filename}' to AWS S3"]}

def test_delete_pdf_file_aws_exception(client, monkeypatch):
    def mock_delete_object(Bucket, Key):
        raise ClientError({"Error": {"Code": "MockException", "Message": "Simulated AWS S3 Error"}}, "delete_object")
    
    monkeypatch.setattr("app.routers.file.s3_client.delete_object", mock_delete_object)
    
    pdf_filename = "python_test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response_upload = client.put("/upload/", files=file)
    assert response_upload.status_code == 200

    response = client.delete(f"/delete/{pdf_filename}")
    assert response.status_code == 500
    assert f"Error while deleting the file '{pdf_filename}' on AWS S3" in response.json()["detail"]

def test_delete_existing_pdf_file(client):
    pdf_filename = "python_test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response_upload = client.put("/upload/", files=file)
    assert response_upload.status_code == 200

    response = client.delete(f"/delete/{pdf_filename}")
    assert response.status_code == 200
    assert response.json() == {'message': f"The file '{pdf_filename}' has been successfully deleted"}

def test_delete_non_existing_pdf_file(client):
    non_existing_pdf_file = "non_existing_python_test_file.pdf"

    response = client.delete(f"/delete/{non_existing_pdf_file}")
    assert response.status_code == 404
    assert response.json() == {'detail': f"The file '{non_existing_pdf_file}' does not exist"}