import os
from io import BytesIO
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from botocore.exceptions import ClientError

from app import models
from app.main import app
from app.database import Base, get_db
from app.utils import MAX_FILE_SIZE_STRING, MAX_FILE_SIZE, MB

DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_upload_pdf_file():
    user_id = 1
    pdf_filename = "test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response = client.post(f"/file/upload/{user_id}", files=file)
    assert response.status_code == 200

    assert response.json()["status"] == 200
    assert response.json()["message"] == "File(s) uploaded successfully!"

    uploaded_file = response.json()["data"][0]
    assert uploaded_file["user_id"] == user_id
    assert "id" in uploaded_file
    assert "url" in uploaded_file
    assert uploaded_file["test_name"] == pdf_filename
    assert "submission_date" in uploaded_file

def test_upload_multiple_pdf_files():
    user_id = 1
    pdf_files = [
        ("test_file1.pdf", b"dummy pdf content 1"),
        ("test_file2.pdf", b"dummy pdf content 2"),
        ("test_file3.pdf", b"dummy pdf content 3")
    ]
    files = [("files", (name, content, "application/pdf")) for name, content in pdf_files]

    response = client.post(f"/file/upload/{user_id}", files=files)
    assert response.status_code == 200

    assert response.json()["status"] == 200
    assert response.json()["message"] == "File(s) uploaded successfully!"

    uploaded_files = response.json()["data"]
    assert len(uploaded_files) == len(pdf_files)

    for uploaded_file, (name, _) in zip(uploaded_files, pdf_files):
        assert uploaded_file["user_id"] == user_id
        assert "id" in uploaded_file
        assert "url" in uploaded_file
        assert uploaded_file["test_name"] == name
        assert "submission_date" in uploaded_file

def test_upload_non_pdf_file():
    user_id = 1
    non_pdf_filename = "test_file.txt"
    non_pdf_content = b"dummy text content"
    file = {"files": (non_pdf_filename, non_pdf_content, "text/plain")}

    response = client.post(f"/file/upload/{user_id}", files=file)
    assert response.status_code == 400
    assert response.json()["status"] == 400
    assert response.json()["message"] == [f"The file '{non_pdf_filename}' is not a PDF, only PDF files are allowed"]

   
def test_upload_large_pdf_file():
    user_id = 1
    large_filename = "test_large_file.pdf"
    large_file_size = MAX_FILE_SIZE + MB
    large_file_content = BytesIO(os.urandom(large_file_size))
    file = {"files": (large_filename, large_file_content, "application/pdf")}

    response = client.post(f"/file/upload/{user_id}", files=file)
    assert response.status_code == 400
    assert response.json()["status"] == 400
    assert response.json()["message"] == [f"The File '{large_filename}' exceeds the size limit of '{MAX_FILE_SIZE_STRING}'"]

def test_upload_pdf_files_aws_exception(monkeypatch):
    def mock_put_object(Bucket, Key, Body):
        raise ClientError({"Error": {"Code": "MockException", "Message": "Simulated AWS S3 Error"}}, "put_object")
    
    monkeypatch.setattr("app.utils.s3_client.put_object", mock_put_object)
    
    user_id = 1
    pdf_filename = "test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response = client.post(f"/file/upload/{user_id}", files=file)
    assert response.status_code == 500
    assert response.json()["status"] == 500
    assert response.json()["message"] == [f"Error while uploading the file '{pdf_filename}' to AWS S3 for user '{user_id}'"]

def test_delete_pdf_file_aws_exception(monkeypatch):
    def mock_delete_object(Bucket, Key):
        raise ClientError({"Error": {"Code": "MockException", "Message": "Simulated AWS S3 Error"}}, "delete_object")
    
    monkeypatch.setattr("app.utils.s3_client.delete_object", mock_delete_object)
    
    user_id = 1
    pdf_filename = "test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}

    response_upload = client.post(f"/file/upload/{user_id}", files=file)
    assert response_upload.status_code == 200

    response_upload_data = response_upload.json()
    file_id = response_upload_data['data'][0]['id']

    response_delete = client.delete(f"/file/delete/{user_id}/{file_id}")
    assert response_delete.status_code == 500
    assert response_delete.json()["detail"] == f"Error while deleting the file '{pdf_filename}' for user '{user_id}' on AWS S3"

def test_delete_existing_pdf_file():
    user_id = 1
    pdf_filename = "test_file.pdf"
    pdf_content = b"dummy pdf content"
    file = {"files": (pdf_filename, pdf_content, "application/pdf")}
    
    response_upload = client.post(f"/file/upload/{user_id}", files=file)
    assert response_upload.status_code == 200
    
    response_upload_data = response_upload.json()
    file_id = response_upload_data['data'][0]['id']
    
    response_delete = client.delete(f"/file/delete/{user_id}/{file_id}")
    assert response_delete.status_code == 200
    assert response_delete.json()["message"] == f"The file '{pdf_filename}' for user '{user_id}' has been successfully deleted"

def test_delete_non_existing_pdf_file():
    user_id = 1
    non_existing_pdf_file_id = 1

    response = client.delete(f"/file/delete/{user_id}/{non_existing_pdf_file_id}")
    assert response.status_code == 404
    assert response.json()["detail"]  == "File not found"

def test_list_user_tests_with_existing_user_id():
    user_id = 1
    with TestingSessionLocal() as db:
        user = models.User(
            id=user_id,
            full_name="Test User",
            email="testuser@example.com",
            password="password",
            birth_date=date(2000, 1, 1),
            biological_sex="M"
        )
        db.add(user)
        db.commit()

        test1 = models.Test(id=1, user_id=user_id, test_name="Test 1", url="http://example.com/test1")
        test2 = models.Test(id=2, user_id=user_id, test_name="Test 2", url="http://example.com/test2")
        test3 = models.Test(id=3, user_id=user_id, test_name="Test 3", url="http://example.com/test3")
        db.add(test1)
        db.add(test2)
        db.add(test3)
        db.commit()

        response = client.get(f"file/tests/{user_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == 200
        assert data["message"] == f"The following tests found for user with ID {user_id}"
        assert len(data["data"]) == 3

def test_list_user_tests_with_non_existing_user_id():
    user_id = 1
    response = client.get(f"file/tests/{user_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"User with ID {user_id} not found"