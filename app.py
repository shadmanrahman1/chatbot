#!/usr/bin/env python3

"""
WhatsApp Bot using Meta's Official WhatsApp Business API
Optimized for Railway deployment with environment variable support
"""

import os
import logging
import mysql.connector
import hmac
import hashlib
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from groq import Groq
from urllib.parse import urlparse


# -------------------------------------------------------------
# Dynamic Database Configuration Helper (Railway/Heroku friendly)
# -------------------------------------------------------------
def build_db_config():
    """Construct DB_CONFIG from explicit vars or DATABASE_URL.
    Supports mysql://user:pass@host:port/dbname
    Falls back to original static values if not present.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            parsed = urlparse(database_url)
            # Expect scheme like mysql or mysql+pymysql
            if not parsed.scheme.startswith("mysql"):
                logger.warning(
                    f"⚠️ Unsupported DATABASE_URL scheme '{parsed.scheme}' – only MySQL variants supported"
                )
            username = parsed.username or "root"
            password = parsed.password or ""
            host = parsed.hostname or "localhost"
            port = parsed.port or 3306
            db_name = (parsed.path or "/edtech_bot").lstrip("/")
            return {
                "host": host,
                "port": port,
                "user": username,
                "password": password,
                "database": db_name,
            }
        except Exception as e:
            logger.error(
                f"❌ Failed to parse DATABASE_URL: {e}. Falling back to explicit config env vars."
            )

    # Fallback to discrete env variables (works for local + Docker)
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "edtech_bot"),
    }


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Meta WhatsApp Business API Configuration
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")  # Railway-friendly name
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")  # Railway-friendly name
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")  # Railway-friendly name
APP_SECRET = os.getenv("APP_SECRET")  # Railway-friendly name
API_VERSION = os.getenv("API_VERSION", "v18.0")
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

# AI Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Database configuration (dynamic to support Railway/Heroku external DBs)
DB_CONFIG = build_db_config()

logger.info("🚀 Starting WhatsApp Bot for Railway deployment...")
logger.info(
    f"🗄️ Database target: {DB_CONFIG.get('host')}:{DB_CONFIG.get('port')}/{DB_CONFIG.get('database')} (user={DB_CONFIG.get('user')})"
)

# Global data storage
COURSES = []
FAQS = []


def get_database_connection():
    """Get database connection with enhanced error handling"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        logger.info("✅ Database connection successful")
        return connection
    except mysql.connector.Error as e:
        logger.error(f"❌ Database connection error: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected database error: {e}")
        return None


def get_courses_from_db():
    """Load courses from database"""
    try:
        connection = get_database_connection()
        if not connection:
            logger.warning("⚠️ No database connection, returning empty courses list")
            return []

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM courses WHERE is_active = 1")
        courses = cursor.fetchall()

        # Convert to the format expected by the bot
        formatted_courses = []
        for course in courses:
            formatted_courses.append(
                {
                    "id": course["id"],
                    "title": course["title"],
                    "description": course["description"],
                    "price": course["price"],
                    "duration": course["duration"],
                    "instructor": course["instructor"],
                }
            )

        logger.info(f"📚 Loaded {len(formatted_courses)} courses from database")
        return formatted_courses

    except Exception as e:
        logger.error(f"❌ Error loading courses: {e}")
        return []
    finally:
        if "connection" in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_faqs_from_db():
    """Load FAQs from database"""
    try:
        connection = get_database_connection()
        if not connection:
            logger.warning("⚠️ No database connection, returning empty FAQs list")
            return []

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM faqs WHERE is_active = 1")
        faqs = cursor.fetchall()

        # Convert to the format expected by the bot
        formatted_faqs = []
        for faq in faqs:
            formatted_faqs.append(
                {
                    "id": faq["id"],
                    "question": faq["question"],
                    "answer": faq["answer"],
                    "keywords": faq.get("keywords", ""),
                }
            )

        logger.info(f"❓ Loaded {len(formatted_faqs)} FAQs from database")
        return formatted_faqs

    except Exception as e:
        logger.error(f"❌ Error loading FAQs: {e}")
        return []
    finally:
        if "connection" in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()


def verify_webhook_signature(payload, signature):
    """Verify webhook signature from Meta"""
    if not APP_SECRET:
        logger.warning("⚠️ APP_SECRET not configured, skipping signature verification")
        return True

    try:
        expected_signature = hmac.new(
            APP_SECRET.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

        # Meta sends signature as 'sha256=<signature>'
        received_signature = signature.replace("sha256=", "") if signature else ""

        return hmac.compare_digest(expected_signature, received_signature)
    except Exception as e:
        logger.error(f"❌ Error verifying webhook signature: {e}")
        return False


def send_whatsapp_message(to_number, message):
    """Send WhatsApp message through Meta's Graph API"""
    try:
        url = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message},
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            logger.info(f"✅ Message sent to {to_number}")
            return True
        else:
            logger.error(
                f"❌ Failed to send message: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"❌ Error sending message: {e}")
        return False


def is_greeting(text):
    """Check if message is a greeting"""
    greetings = [
        "hello",
        "hi",
        "hey",
        "start",
        "salam",
        "assalam",
        "good morning",
        "good evening",
        "namaste",
        "adaab",
    ]
    return any(greeting in text.lower() for greeting in greetings)


def search_faqs(query):
    """Search for relevant FAQs"""
    query_lower = query.lower()
    relevant_faqs = []

    for faq in FAQS:
        search_text = (
            f"{faq['question']} {faq['answer']} {faq.get('keywords', '')}".lower()
        )
        if any(word in search_text for word in query_lower.split() if len(word) > 2):
            relevant_faqs.append(faq)

    return relevant_faqs[:3]  # Return max 3 FAQs


def search_courses(query):
    """Search for courses with improved keyword matching"""
    query_lower = query.lower().strip()
    relevant_courses = []

    # Define specific course keywords
    course_keywords = {
        "python": [
            "python",
            "programming",
            "script",
            "py",
            "data science",
            "pandas",
            "numpy",
        ],
        "java": ["java", "spring", "jvm", "enterprise", "bootcamp"],
        "javascript": ["javascript", "js", "node", "web"],
        "react": ["react", "jsx", "component", "frontend", "web development"],
        "data": [
            "data",
            "science",
            "analytics",
            "machine learning",
            "ml",
            "ai",
            "analysis",
        ],
        "web": ["web", "development", "html", "css", "frontend", "responsive"],
        "mobile": ["mobile", "app", "android", "ios", "react native"],
    }

    # First, try exact keyword matching
    matched_courses = []
    for category, keywords in course_keywords.items():
        for keyword in keywords:
            if keyword in query_lower:
                # Look for courses that match this keyword
                for course in COURSES:
                    course_text = f"{course['title']} {course['description']}".lower()
                    if keyword in course_text and course not in matched_courses:
                        matched_courses.append(course)

    if matched_courses:
        # Sort by title relevance first
        title_matches = [
            c
            for c in matched_courses
            if any(word in c["title"].lower() for word in query_lower.split())
        ]
        desc_matches = [c for c in matched_courses if c not in title_matches]
        return title_matches + desc_matches

    # Fallback: general search
    for course in COURSES:
        course_text = f"{course['title']} {course['description']}".lower()
        query_words = [word for word in query_lower.split() if len(word) > 2]
        matches = sum(1 for word in query_words if word in course_text)
        if matches > 0:
            relevant_courses.append(course)

    return relevant_courses


def format_course_response(courses, query):
    """Format course search results into a response"""
    if not courses:
        return f"❌ No courses found for '{query}'. Try searching for: Python, Java, JavaScript, React, or Data Science."

    if len(courses) == 1:
        course = courses[0]
        return f"""📚 **{course["title"]}**
💰 Price: ${course["price"]}
⏱️ Duration: {course["duration"]} weeks
👨‍🏫 Instructor: {course["instructor"]}
📝 {course["description"]}

🎯 This looks like exactly what you're looking for!
💡 Ready to enroll? Just let me know!"""
    else:
        response = f"🔍 Found {len(courses)} courses related to '{query}':\n\n"
        for i, course in enumerate(courses, 1):
            response += f"{i}. **{course['title']}** - ${course['price']} ({course['duration']} weeks)\n"
            response += f"   👨‍🏫 {course['instructor']}\n\n"

        response += "💡 Would you like details about any specific course? Just ask!"
        return response


def get_ai_response(user_message):
    """Get AI response from Groq with database context"""
    try:
        if not GROQ_API_KEY:
            logger.warning("⚠️ GROQ_API_KEY not found")
            return "I'm here to help with course information! Ask me about our Python, Java, React, or Data Science courses."

        client = Groq(api_key=GROQ_API_KEY)

        # Create course context from database
        course_info = "\n".join(
            [
                f"- {course['title']}: {course['description']} (${course['price']}, {course['duration']} weeks, Instructor: {course['instructor']})"
                for course in COURSES[:5]  # Limit to avoid token limits
            ]
        )

        # Create FAQ context from database
        faq_info = "\n".join(
            [
                f"Q: {faq['question']}\nA: {faq['answer']}"
                for faq in FAQS[:3]  # Include top 3 FAQs
            ]
        )

        system_prompt = f"""You are a helpful EdTech WhatsApp bot assistant. Be friendly, encouraging, and educational.

Available Courses:
{course_info}

Common FAQs:
{faq_info}

Keep responses concise (under 200 words), helpful, and focused on education. Always encourage learning and reference our actual courses when relevant."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=200,
        )

        ai_response = response.choices[0].message.content
        logger.info(f"🤖 AI Response generated for: {user_message[:50]}...")
        return ai_response

    except Exception as e:
        logger.error(f"❌ AI response error: {e}")
        return "I'm here to help with course information and answer your questions about our educational programs. What would you like to know?"


def process_message(message_text, from_number):
    """Process incoming message and generate response"""
    try:
        logger.info(f"📨 Processing message from {from_number}: {message_text}")

        # Handle greetings
        if is_greeting(message_text):
            available_courses = (
                "\n".join([f"• {course['title']}" for course in COURSES[:5]])
                if COURSES
                else "• Loading courses..."
            )
            return f"""🎓 Welcome to our EdTech Learning Platform!

📚 **Available Courses:**
{available_courses}

💡 **How can I help you today?**
Ask me about:
• Course details and curriculum
• Pricing and enrollment
• Prerequisites for any course
• Career guidance

Just type your question, and I'll provide detailed information! 🚀"""

        # Search for courses first (priority)
        courses = search_courses(message_text)
        if courses:
            return format_course_response(courses, message_text)

        # Search FAQs
        faqs = search_faqs(message_text)
        if faqs:
            response = "❓ **Here's what I found:**\n\n"
            for i, faq in enumerate(faqs, 1):
                response += f"{i}. **{faq['question']}**\n{faq['answer']}\n\n"
            response += "💡 Need more details? Feel free to ask!"
            return response

        # Fallback to AI response
        return get_ai_response(message_text)

    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")
        return "I apologize for the technical issue. Please try asking about our courses or contact support."


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Handle Meta WhatsApp webhook"""
    if request.method == "GET":
        # Webhook verification - Meta sends these parameters
        hub_mode = request.args.get("hub.mode")
        hub_verify_token = request.args.get("hub.verify_token")
        hub_challenge = request.args.get("hub.challenge")

        logger.info(f"🔍 Webhook verification request:")
        logger.info(f"   Mode: {hub_mode}")
        logger.info(f"   Token received: {hub_verify_token}")
        logger.info(f"   Challenge: {hub_challenge}")
        logger.info(f"   Expected token: {VERIFY_TOKEN}")

        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            logger.info("✅ Webhook verification successful!")
            return hub_challenge, 200
        else:
            logger.error("❌ Webhook verification failed!")
            return "Forbidden", 403

    elif request.method == "POST":
        try:
            # Get raw payload for signature verification
            payload = request.get_data()
            signature = request.headers.get("X-Hub-Signature-256", "")

            # Verify signature (optional but recommended)
            if not verify_webhook_signature(payload, signature):
                logger.error("❌ Invalid webhook signature")
                return "Forbidden", 403

            data = request.get_json()
            logger.info(f"🔔 Webhook received: {data}")

            # Process webhook data
            if data.get("object") == "whatsapp_business_account":
                entries = data.get("entry", [])

                for entry in entries:
                    changes = entry.get("changes", [])

                    for change in changes:
                        if change.get("field") == "messages":
                            value = change.get("value", {})
                            messages = value.get("messages", [])

                            for message in messages:
                                from_number = message.get("from")
                                message_type = message.get("type")

                                if message_type == "text":
                                    text_body = message.get("text", {}).get("body", "")

                                    # Process the message
                                    response = process_message(text_body, from_number)

                                    # Send response
                                    if response:
                                        send_success = send_whatsapp_message(
                                            from_number, response
                                        )
                                        if send_success:
                                            logger.info(
                                                f"✅ Response sent to {from_number}"
                                            )
                                        else:
                                            logger.error(
                                                f"❌ Failed to send response to {from_number}"
                                            )

            return jsonify({"status": "ok"}), 200

        except Exception as e:
            logger.error(f"❌ Webhook processing error: {e}")
            return jsonify({"error": "Internal server error"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Railway monitoring"""
    db_status = "connected" if get_database_connection() else "disconnected"
    return jsonify(
        {
            "status": "healthy",
            "service": "WhatsApp EdTech Bot",
            "api": "Meta WhatsApp Business API",
            "courses": len(COURSES),
            "faqs": len(FAQS),
            "database": db_status,
            "environment": "railway",
        }
    ), 200


@app.route("/", methods=["GET"])
def home():
    """Home endpoint"""
    return jsonify(
        {
            "message": "🤖 WhatsApp EdTech Bot is running!",
            "endpoints": {"webhook": "/webhook", "health": "/health", "test": "/test"},
            "status": "active",
        }
    ), 200


@app.route("/test", methods=["POST"])
def test_message():
    """Test endpoint to simulate a message"""
    data = request.get_json()
    test_message = data.get("message", "hello")
    test_number = data.get("number", "1234567890")

    response = process_message(test_message, test_number)
    return jsonify(
        {
            "input": test_message,
            "response": response,
            "courses_count": len(COURSES),
            "faqs_count": len(FAQS),
        }
    ), 200


# Initialize data on startup
def initialize_data():
    """Load data from database on startup"""
    global COURSES, FAQS
    logger.info("🔄 Initializing data from database...")

    COURSES = get_courses_from_db()
    FAQS = get_faqs_from_db()

    logger.info(f"✅ Initialization complete: {len(COURSES)} courses, {len(FAQS)} FAQs")


if __name__ == "__main__":
    logger.info("🚀 Starting WhatsApp EdTech Bot for Railway...")

    # Verify configuration
    missing_config = []
    if not WHATSAPP_TOKEN:
        missing_config.append("WHATSAPP_TOKEN")
    if not PHONE_NUMBER_ID:
        missing_config.append("PHONE_NUMBER_ID")
    if not VERIFY_TOKEN:
        missing_config.append("VERIFY_TOKEN")

    if missing_config:
        logger.error(
            f"❌ Missing required environment variables: {', '.join(missing_config)}"
        )
    else:
        logger.info("✅ All required environment variables configured")

    if not GROQ_API_KEY:
        logger.warning("⚠️ GROQ_API_KEY not configured - AI responses will use fallback")

    # Load data from database
    initialize_data()

    # Get port from environment (Railway sets this)
    port = int(os.getenv("PORT", 5000))

    logger.info(f"🌐 Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # For production (gunicorn), initialize data when module is imported
    initialize_data()
