import requests
import time


def test_seed():
    """Test seeding via health endpoint"""
    base_url = "https://web-production-e9648.up.railway.app"

    # Check current status
    print("🔍 Checking current database status...")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"Current: {data.get('courses', 0)} courses, {data.get('faqs', 0)} FAQs")

        if data.get("courses", 0) == 0:
            print("\n🌱 Attempting to seed database...")

            # Try seeding via GET parameter
            response = requests.get(f"{base_url}/health?seed=true")
            if response.status_code == 200:
                result = response.json()
                if result.get("seeded", False):
                    print("✅ Seeded successfully!")
                    print(
                        f"New counts: {result.get('courses', 0)} courses, {result.get('faqs', 0)} FAQs"
                    )
                    return True
                else:
                    print("❌ Seeding not available yet (Railway still deploying)")

            # Try seeding via POST
            try:
                response = requests.post(f"{base_url}/health", json={"seed": True})
                if response.status_code == 200:
                    result = response.json()
                    if result.get("seeded", False):
                        print("✅ Seeded successfully via POST!")
                        print(
                            f"New counts: {result.get('courses', 0)} courses, {result.get('faqs', 0)} FAQs"
                        )
                        return True
            except Exception as e:
                print(f"POST attempt failed: {e}")

        else:
            print("✅ Database already has data!")
            return True

    return False


if __name__ == "__main__":
    success = False
    for attempt in range(3):
        if attempt > 0:
            print(
                f"\n⏳ Waiting 30 seconds for Railway deployment... (attempt {attempt + 1})"
            )
            time.sleep(30)

        success = test_seed()
        if success:
            break

    if not success:
        print("\n❌ Unable to seed database. Railway may still be deploying.")
        print(
            "💡 You can manually try: https://web-production-e9648.up.railway.app/health?seed=true"
        )
