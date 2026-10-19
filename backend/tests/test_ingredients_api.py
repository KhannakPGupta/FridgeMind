"""Tests for ingredient recognition and manual normalization endpoints."""

import io
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def create_test_image(format="JPEG", size=(100, 100)) -> bytes:
    """Generate a small valid in-memory image for upload testing."""
    img = Image.new("RGB", size, color=(255, 200, 100))
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def test_normalize_manual_ingredients():
    """Verify normalization, emoji assignment, and deduplication of user input."""
    payload = {
        "items": [
            "3 eggs",
            "tomatoes",
            "200g paneer",
            "paneer",  # duplicate
            "spinach",
            "dahi",
        ]
    }
    response = client.post("/api/ingredients/normalize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["duplicates_removed"] == 1
    assert len(data["ingredients"]) == 5

    names = [i["name"] for i in data["ingredients"]]
    assert "Eggs" in names
    assert "Tomato" in names
    assert "Paneer" in names
    assert "Spinach" in names
    assert "Yogurt" in names

    # Verify emoji mapping
    egg_item = next(i for i in data["ingredients"] if i["name"] == "Eggs")
    assert egg_item["emoji"] == "🥚"
    assert egg_item["qty"] == "3"


def test_recognize_fridge_photo_success():
    """Verify valid image upload returns structured ingredient response."""
    img_bytes = create_test_image("JPEG")
    files = {"file": ("test_fridge.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/ingredients/recognize", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "ingredients" in data
    assert len(data["ingredients"]) > 0
    assert "detected_count" in data
    assert "source" in data


def test_recognize_fridge_photo_invalid_media_type():
    """Verify non-image upload is rejected with 415."""
    files = {"file": ("notes.txt", b"just some text", "text/plain")}
    response = client.post("/api/ingredients/recognize", files=files)
    assert response.status_code == 415


def test_recognize_fridge_photo_corrupted_image():
    """Verify unreadable image file is rejected with 400."""
    files = {"file": ("corrupt.jpg", b"not a real image data at all", "image/jpeg")}
    response = client.post("/api/ingredients/recognize", files=files)
    assert response.status_code == 400
