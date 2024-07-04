import os
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from app.main import app
from app.database import get_db
from app.utils import MAX_FILE_SIZE_STRING, MAX_FILE_SIZE, MB

mock_session = MagicMock()
def override_get_db():
    try:
        yield mock_session
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def mock_db_session():
    return mock_session

@pytest.fixture
def client():
    return TestClient(app)

def test_upload_pdf_file(client):
    user_id = 1
    pdf_filename = "python_test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response = client.post(f"/data/upload/{user_id}", files=file)
    assert response.status_code == 200
    assert {'message': [f"The file '{pdf_filename}' has been successfully uploaded for user '{user_id}'"]}

def test_upload_multiple_pdf_files(client):
    user_id = 1
    pdf_files = [
        ("python_test_file1.pdf", b"dummy pdf content 1"),
        ("python_test_file2.pdf", b"dummy pdf content 2"),
        ("python_test_file3.pdf", b"dummy pdf content 3")
    ]
    files = [("files", (name, content, "application/pdf")) for name, content in pdf_files]

    response = client.post(f"/data/upload/{user_id}", files=files)
    assert response.status_code == 200
    uploaded_files = [f"The file '{name}' has been successfully uploaded for user '{user_id}'" for name, _ in pdf_files]
    assert response.json() == {'message': uploaded_files}

def test_upload_non_pdf_file(client):
    user_id = 1
    non_pdf_filename = "python_test_file.txt"
    non_pdf_content = b"dummy text content"
    file = {"files": (non_pdf_filename, non_pdf_content, "text/plain")}

    response = client.post(f"/data/upload/{user_id}", files=file)
    assert response.status_code == 400
    assert response.json() == {'message': [f"The file '{non_pdf_filename}' is not a PDF, only PDF files are allowed"]}
   
def test_upload_large_pdf_file(client):
    user_id = 1
    large_filename = "python_test_large_file.pdf"
    large_file_size = MAX_FILE_SIZE + MB
    large_file_content = BytesIO(os.urandom(large_file_size))
    file = {"files": (large_filename, large_file_content, "application/pdf")}

    response = client.post(f"/data/upload/{user_id}", files=file)
    assert response.status_code == 400
    assert response.json() == {'message': [f"The File '{large_filename}' exceeds the size limit of '{MAX_FILE_SIZE_STRING}'"]}

def test_upload_pdf_files_aws_exception(client, monkeypatch):
    def mock_put_object(Bucket, Key, Body):
        raise ClientError({"Error": {"Code": "MockException", "Message": "Simulated AWS S3 Error"}}, "put_object")
    
    monkeypatch.setattr("app.routers.file.s3_client.put_object", mock_put_object)
    
    user_id = 1
    pdf_filename = "python_test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response = client.post(f"/data/upload/{user_id}", files=file)
    assert response.status_code == 500
    assert response.json() == {'message': [f"Error while uploading the file '{pdf_filename}' to AWS S3 for user '{user_id}'"]}

def test_delete_pdf_file_aws_exception(client, monkeypatch):
    def mock_delete_object(Bucket, Key):
        raise ClientError({"Error": {"Code": "MockException", "Message": "Simulated AWS S3 Error"}}, "delete_object")
    
    monkeypatch.setattr("app.routers.file.s3_client.delete_object", mock_delete_object)
    
    user_id = 1
    pdf_filename = "python_test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response_upload = client.post(f"/data/upload/{user_id}", files=file)
    assert response_upload.status_code == 200

    response = client.delete(f"/data/delete/{user_id}/{pdf_filename}")
    assert response.status_code == 500
    assert f"Error while deleting the file '{pdf_filename}' for user '{user_id}' on AWS S3" in response.json()["detail"]

def test_delete_existing_pdf_file(client):
    user_id = 1
    pdf_filename = "python_test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response_upload = client.post(f"/data/upload/{user_id}", files=file)
    assert response_upload.status_code == 200

    response = client.delete(f"/data/delete/{user_id}/{pdf_filename}")
    assert response.status_code == 200
    assert response.json() == {'message': f"The file '{pdf_filename}' for user '{user_id}' has been successfully deleted"}

def test_delete_non_existing_pdf_file(client):
    user_id = 1
    non_existing_pdf_file = "non_existing_python_test_file.pdf"

    response = client.delete(f"/data/delete/{user_id}/{non_existing_pdf_file}")
    assert response.status_code == 404
    assert response.json() == {'detail': f"The file '{non_existing_pdf_file}' for user '{user_id}' does not exist"}