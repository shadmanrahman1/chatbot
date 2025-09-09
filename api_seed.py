"""
Simple script to seed Railway database via HTTP endpoint
"""

import requests
import json


def seed_via_api():
    """Seed database by calling a seeding endpoint"""

    url = "https://web-production-e9648.up.railway.app/seed"

    print("🌱 Requesting database seeding...")

    try:
        response = requests.post(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print("✅ Seeding successful!")
            print(f"📚 Courses: {data.get('courses_added', 0)}")
            print(f"❓ FAQs: {data.get('faqs_added', 0)}")
            return True
        else:
            print(f"❌ Seeding failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    seed_via_api()
