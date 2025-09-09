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

VERSION = os.getenv("APP_VERSION", "v0.2.0")
BUILD_COMMIT = os.getenv("RAILWAY_GIT_COMMIT_SHA", os.getenv("GIT_SHA", "unknown"))
STARTUP_PHASE = {"ready": False}

logger.info(
    f"🚀 Starting WhatsApp Bot for Railway deployment (version={VERSION}, commit={BUILD_COMMIT[:7]})"
)
logger.info(
    f"🗄️ Database target: {DB_CONFIG.get('host')}:{DB_CONFIG.get('port')}/{DB_CONFIG.get('database')} (user={DB_CONFIG.get('user')})"
)

# Global data storage
COURSES = []
FAQS = []


def get_database_connection():
    """Get database connection with enhanced error handling.
    Uses a short timeout so startup isn't blocked if DB is slow/unavailable."""
    try:
        connection = mysql.connector.connect(
            **DB_CONFIG,
            connection_timeout=5,
        )
        return connection
    except mysql.connector.Error as e:
        logger.warning(f"⚠️ DB connection issue (non-fatal): {e}")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Unexpected DB error (non-fatal): {e}")
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
    if not APP_SECRET or APP_SECRET == "your_app_secret_here":
        logger.warning(
            "⚠️ APP_SECRET not configured or using placeholder, skipping signature verification"
        )
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

        logger.info(f"🌐 API Call: POST {url}")
        logger.info(f"🔑 Using token: ...{WHATSAPP_TOKEN[-10:] if WHATSAPP_TOKEN else 'NONE'}")
        logger.info(f"📞 To: {to_number}, Phone ID: {PHONE_NUMBER_ID}")

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"🔄 API Response: {response.status_code}")
        logger.info(f"📄 Response body: {response.text}")

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

        logger.info("🔍 Webhook verification request:")
        logger.info(f"   Mode: {hub_mode}")
        logger.info(f"   Token received: {hub_verify_token}")
        logger.info(f"   Challenge: {hub_challenge}")
        logger.info(f"   Expected token: {VERIFY_TOKEN}")
        logger.info(f"   Token match: {hub_verify_token == VERIFY_TOKEN}")
        logger.info(f"   VERIFY_TOKEN is set: {bool(VERIFY_TOKEN)}")
        logger.info(
            f"   VERIFY_TOKEN length: {len(VERIFY_TOKEN) if VERIFY_TOKEN else 0}"
        )

        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            logger.info("✅ Webhook verification successful!")
            return hub_challenge, 200
        else:
            logger.error("❌ Webhook verification failed!")
            return "Forbidden", 403

    elif request.method == "POST":
        try:
            # Signature verification temporarily disabled for testing
            logger.info("🔍 Webhook signature check bypassed for testing")

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
                                
                                logger.info(f"📱 Processing message: type={message_type}, from={from_number}")

                                if message_type == "text":
                                    text_body = message.get("text", {}).get("body", "")
                                    logger.info(f"📝 Message text: '{text_body}'")

                                    # Process the message
                                    response = process_message(text_body, from_number)
                                    logger.info(f"🤖 Generated response length: {len(response) if response else 0}")

                                    # Send response
                                    if response:
                                        logger.info(f"📤 Attempting to send message to {from_number}")
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
                                    else:
                                        logger.error(f"❌ No response generated for message: '{text_body}'")

            return jsonify({"status": "ok"}), 200

        except Exception as e:
            logger.error(f"❌ Webhook processing error: {e}")
            return jsonify({"error": "Internal server error"}), 500


@app.route("/health", methods=["GET", "POST"])
def health():
    """Health check endpoint for Railway monitoring with optional seeding"""
    try:
        _lazy_bootstrap()  # Ensure initialization

        # Check for seed parameter
        seed_requested = False
        if request.method == "POST":
            data = request.get_json() or {}
            seed_requested = (
                data.get("seed", False) or request.args.get("seed") == "true"
            )
        elif request.method == "GET":
            seed_requested = request.args.get("seed") == "true"

        connection = get_database_connection()
        db_status = "connected" if connection else "disconnected"

        # Declare globals at start of function
        global COURSES, FAQS
        course_count = len(COURSES)
        faq_count = len(FAQS)

        if connection and seed_requested:
            try:
                cursor = connection.cursor()
                logger.info("🌱 Seeding requested via health endpoint")

                # Create tables if not exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS courses (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        description TEXT NOT NULL,
                        price DECIMAL(10,2) NOT NULL,
                        duration INT NOT NULL,
                        instructor VARCHAR(255) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS faqs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        question VARCHAR(500) NOT NULL,
                        answer TEXT NOT NULL,
                        keywords VARCHAR(500),
                        course_id INT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
                    )
                """)

                # Clear and insert data
                cursor.execute("DELETE FROM faqs")
                cursor.execute("DELETE FROM courses")

                # Insert courses
                courses_data = [
                    (
                        "Python Programming Fundamentals",
                        "Learn Python from scratch. Covers variables, data types, loops, functions, and object-oriented programming. Perfect for beginners wanting to start their coding journey.",
                        299.99,
                        8,
                        "John Smith",
                        True,
                    ),
                    (
                        "Java Development Bootcamp",
                        "Comprehensive Java course covering OOP, Spring Framework, and enterprise development. Build real-world applications and learn industry best practices.",
                        399.99,
                        12,
                        "Sarah Johnson",
                        True,
                    ),
                    (
                        "Web Development with React",
                        "Master modern web development using React.js, HTML5, CSS3, and JavaScript. Build responsive websites and single-page applications.",
                        349.99,
                        10,
                        "Mike Davis",
                        True,
                    ),
                    (
                        "Data Science with Python",
                        "Learn data analysis, machine learning, and visualization using Python, Pandas, NumPy, and Scikit-learn. Perfect for aspiring data scientists.",
                        449.99,
                        14,
                        "Dr. Emily Chen",
                        True,
                    ),
                    (
                        "Mobile App Development",
                        "Create mobile apps for iOS and Android using React Native. Learn app deployment, UI/UX design, and mobile-specific development patterns.",
                        379.99,
                        12,
                        "Alex Rodriguez",
                        True,
                    ),
                ]

                cursor.executemany(
                    """
                    INSERT INTO courses (title, description, price, duration, instructor, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    courses_data,
                )

                # Insert FAQs
                faqs_data = [
                    (
                        "What programming courses do you offer?",
                        "We offer Python Programming, Java Development, Web Development with React, Data Science with Python, and Mobile App Development. All courses are designed for practical, hands-on learning.",
                        "courses, programming, languages, available",
                        None,
                        True,
                    ),
                    (
                        "What are your office hours?",
                        "Our support team is available Monday to Friday, 9 AM to 6 PM (GMT+6). You can also reach us via WhatsApp anytime for quick questions!",
                        "office hours, support, contact, time",
                        None,
                        True,
                    ),
                    (
                        "How do I enroll in a course?",
                        "Enrollment is easy! Just message us with the course you are interested in, and we will guide you through the process. You can pay online or through mobile banking.",
                        "enroll, enrollment, registration, signup",
                        None,
                        True,
                    ),
                    (
                        "Do you provide certificates?",
                        "Yes! All students receive a completion certificate after successfully finishing their course. Our certificates are industry-recognized and can boost your career prospects.",
                        "certificate, certification, completion, credentials",
                        None,
                        True,
                    ),
                    (
                        "What payment methods do you accept?",
                        "We accept online payments, mobile banking (bKash, Nagad, Rocket), and bank transfers. We also offer installment plans for courses over $300.",
                        "payment, money, cost, price, bkash, nagad",
                        None,
                        True,
                    ),
                    (
                        "How much does the Python course cost?",
                        "The Python Programming Fundamentals course costs $299.99. This includes 8 weeks of instruction, hands-on projects, and lifetime access to course materials.",
                        "python, price, cost, fee",
                        1,
                        True,
                    ),
                    (
                        "Is Python course good for beginners?",
                        "Absolutely! Our Python course is designed specifically for beginners. No prior programming experience required. We start from the very basics and gradually build up to advanced concepts.",
                        "python, beginner, basic, start, new",
                        1,
                        True,
                    ),
                    (
                        "What does the Java course include?",
                        "The Java Development Bootcamp covers Core Java, Object-Oriented Programming, Spring Framework, database connectivity, and enterprise development. Duration: 12 weeks. Price: $399.99.",
                        "java, includes, content, curriculum",
                        2,
                        True,
                    ),
                    (
                        "Do I need to know HTML before taking React course?",
                        "Basic HTML/CSS knowledge is helpful but not required. Our Web Development course covers HTML5, CSS3, JavaScript fundamentals before diving into React.js.",
                        "react, web, html, css, prerequisites",
                        3,
                        True,
                    ),
                    (
                        "Do you offer support after course completion?",
                        "Yes! We provide 6 months of post-course support including career guidance, project reviews, and technical assistance. Our community forum is also available 24/7.",
                        "support, help, after, completion, assistance",
                        None,
                        True,
                    ),
                    (
                        "Can I get a refund if I am not satisfied?",
                        "We offer a 7-day money-back guarantee. If you are not satisfied within the first week, we will provide a full refund, no questions asked.",
                        "refund, money back, satisfaction, guarantee",
                        None,
                        True,
                    ),
                ]

                cursor.executemany(
                    """
                    INSERT INTO faqs (question, answer, keywords, course_id, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    faqs_data,
                )

                connection.commit()

                # Reload global data (global already declared above)
                COURSES = get_courses_from_db()
                FAQS = get_faqs_from_db()

                # Update counts
                course_count = len(COURSES)
                faq_count = len(FAQS)

                logger.info("✅ Database seeded successfully via health endpoint")
                cursor.close()

            except Exception as e:
                logger.error(f"Seeding error: {e}")
            finally:
                if connection.is_connected():
                    connection.close()

        response_data = {
            "status": "healthy",
            "service": "WhatsApp EdTech Bot",
            "api": "Meta WhatsApp Business API",
            "courses": course_count,
            "faqs": faq_count,
            "database": db_status,
            "environment": "railway",
        }

        if seed_requested:
            response_data["seeded"] = True
            response_data["message"] = "Database seeding attempted"

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    """Home endpoint"""
    _lazy_bootstrap()  # Ensure initialization
    return jsonify(
        {
            "message": "🤖 WhatsApp EdTech Bot v2.1 is running with seeding!",
            "endpoints": {
                "webhook": "/webhook",
                "health": "/health",
                "test": "/test",
                "seed": "/seed",
                "ready": "/ready",
                "meta": "/meta",
            },
            "status": "active",
            "version": VERSION,
            "commit": BUILD_COMMIT[:7],
        }
    ), 200


@app.route("/test", methods=["POST"])
def test_message():
    """Test endpoint to simulate a message"""
    _lazy_bootstrap()  # Ensure initialization
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


@app.route("/seed", methods=["POST"])
def seed_database():
    """Seed database with courses and FAQs"""
    try:
        connection = get_database_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = connection.cursor()

        # Create courses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                duration INT NOT NULL,
                instructor VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        # Create faqs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faqs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                question VARCHAR(500) NOT NULL,
                answer TEXT NOT NULL,
                keywords VARCHAR(500),
                course_id INT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
            )
        """)

        # Clear existing data
        cursor.execute("DELETE FROM faqs")
        cursor.execute("DELETE FROM courses")

        # Insert courses
        courses_data = [
            (
                "Python Programming Fundamentals",
                "Learn Python from scratch. Covers variables, data types, loops, functions, and object-oriented programming. Perfect for beginners wanting to start their coding journey.",
                299.99,
                8,
                "John Smith",
                True,
            ),
            (
                "Java Development Bootcamp",
                "Comprehensive Java course covering OOP, Spring Framework, and enterprise development. Build real-world applications and learn industry best practices.",
                399.99,
                12,
                "Sarah Johnson",
                True,
            ),
            (
                "Web Development with React",
                "Master modern web development using React.js, HTML5, CSS3, and JavaScript. Build responsive websites and single-page applications.",
                349.99,
                10,
                "Mike Davis",
                True,
            ),
            (
                "Data Science with Python",
                "Learn data analysis, machine learning, and visualization using Python, Pandas, NumPy, and Scikit-learn. Perfect for aspiring data scientists.",
                449.99,
                14,
                "Dr. Emily Chen",
                True,
            ),
            (
                "Mobile App Development",
                "Create mobile apps for iOS and Android using React Native. Learn app deployment, UI/UX design, and mobile-specific development patterns.",
                379.99,
                12,
                "Alex Rodriguez",
                True,
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO courses (title, description, price, duration, instructor, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            courses_data,
        )

        # Insert FAQs
        faqs_data = [
            (
                "What programming courses do you offer?",
                "We offer Python Programming, Java Development, Web Development with React, Data Science with Python, and Mobile App Development. All courses are designed for practical, hands-on learning.",
                "courses, programming, languages, available",
                None,
                True,
            ),
            (
                "What are your office hours?",
                "Our support team is available Monday to Friday, 9 AM to 6 PM (GMT+6). You can also reach us via WhatsApp anytime for quick questions!",
                "office hours, support, contact, time",
                None,
                True,
            ),
            (
                "How do I enroll in a course?",
                "Enrollment is easy! Just message us with the course you are interested in, and we will guide you through the process. You can pay online or through mobile banking.",
                "enroll, enrollment, registration, signup",
                None,
                True,
            ),
            (
                "Do you provide certificates?",
                "Yes! All students receive a completion certificate after successfully finishing their course. Our certificates are industry-recognized and can boost your career prospects.",
                "certificate, certification, completion, credentials",
                None,
                True,
            ),
            (
                "What payment methods do you accept?",
                "We accept online payments, mobile banking (bKash, Nagad, Rocket), and bank transfers. We also offer installment plans for courses over $300.",
                "payment, money, cost, price, bkash, nagad",
                None,
                True,
            ),
            (
                "How much does the Python course cost?",
                "The Python Programming Fundamentals course costs $299.99. This includes 8 weeks of instruction, hands-on projects, and lifetime access to course materials.",
                "python, price, cost, fee",
                1,
                True,
            ),
            (
                "Is Python course good for beginners?",
                "Absolutely! Our Python course is designed specifically for beginners. No prior programming experience required. We start from the very basics and gradually build up to advanced concepts.",
                "python, beginner, basic, start, new",
                1,
                True,
            ),
            (
                "What does the Java course include?",
                "The Java Development Bootcamp covers Core Java, Object-Oriented Programming, Spring Framework, database connectivity, and enterprise development. Duration: 12 weeks. Price: $399.99.",
                "java, includes, content, curriculum",
                2,
                True,
            ),
            (
                "Do I need to know HTML before taking React course?",
                "Basic HTML/CSS knowledge is helpful but not required. Our Web Development course covers HTML5, CSS3, JavaScript fundamentals before diving into React.js.",
                "react, web, html, css, prerequisites",
                3,
                True,
            ),
            (
                "Do you offer support after course completion?",
                "Yes! We provide 6 months of post-course support including career guidance, project reviews, and technical assistance. Our community forum is also available 24/7.",
                "support, help, after, completion, assistance",
                None,
                True,
            ),
            (
                "Can I get a refund if I am not satisfied?",
                "We offer a 7-day money-back guarantee. If you are not satisfied within the first week, we will provide a full refund, no questions asked.",
                "refund, money back, satisfaction, guarantee",
                None,
                True,
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO faqs (question, answer, keywords, course_id, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """,
            faqs_data,
        )

        connection.commit()

        # Verify counts
        cursor.execute("SELECT COUNT(*) FROM courses")
        course_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM faqs")
        faq_count = cursor.fetchone()[0]

        # Reload global data
        global COURSES, FAQS
        COURSES = get_courses_from_db()
        FAQS = get_faqs_from_db()

        logger.info(f"🌱 Database seeded: {course_count} courses, {faq_count} FAQs")

        return jsonify(
            {
                "success": True,
                "courses_added": course_count,
                "faqs_added": faq_count,
                "message": "Database seeded successfully",
            }
        ), 200

    except Exception as e:
        logger.error(f"❌ Seeding error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "connection" in locals() and connection.is_connected():
            connection.close()


def initialize_data(force: bool = False):
    """Load data from database.
    Only runs if local caches empty unless force=True.
    """
    global COURSES, FAQS
    if COURSES and FAQS and not force:
        return
    logger.info("🔄 Loading data from database (lazy)...")
    new_courses = get_courses_from_db()
    new_faqs = get_faqs_from_db()
    if new_courses:
        COURSES = new_courses
    if new_faqs:
        FAQS = new_faqs
    logger.info(
        f"✅ Data ready: {len(COURSES)} courses, {len(FAQS)} FAQs (force={force})"
    )


# Lazy bootstrap function - called on first request
def _lazy_bootstrap():
    """Ensure data is loaded only once per process just before serving traffic."""
    if not STARTUP_PHASE["ready"]:
        initialize_data()
        STARTUP_PHASE["ready"] = True


@app.route("/ready", methods=["GET"])
def readiness():
    """Lightweight readiness probe (fast, no DB round trip)."""
    _lazy_bootstrap()  # Ensure initialization on first request
    return jsonify(
        {
            "ready": STARTUP_PHASE["ready"],
            "version": VERSION,
            "commit": BUILD_COMMIT[:7],
        }
    ), 200


@app.route("/meta", methods=["GET"])
def meta_info():
    """Service metadata for debugging deployments."""
    return jsonify(
        {
            "service": "whatsapp-edtech-bot",
            "version": VERSION,
            "commit": BUILD_COMMIT,
            "python": os.getenv("PYTHON_VERSION", "unknown"),
            "db_host": DB_CONFIG.get("host"),
            "db_name": DB_CONFIG.get("database"),
            "loaded_courses": len(COURSES),
            "loaded_faqs": len(FAQS),
            "lazy_ready": STARTUP_PHASE["ready"],
        }
    ), 200


def _log_config_state():
    missing = []
    if not WHATSAPP_TOKEN:
        missing.append("WHATSAPP_TOKEN")
    if not PHONE_NUMBER_ID:
        missing.append("PHONE_NUMBER_ID")
    if not VERIFY_TOKEN:
        missing.append("VERIFY_TOKEN")
    if missing:
        logger.warning(f"⚠️ Missing env vars: {', '.join(missing)}")
    if not GROQ_API_KEY:
        logger.warning("⚠️ GROQ_API_KEY not set – AI replies downgraded")


_log_config_state()

if __name__ == "__main__":
    # Local dev: trigger lazy load (non-blocking if DB down)
    initialize_data()
    port = int(os.getenv("PORT", 5000))
    logger.info(f"🌐 Dev server on :{port} (lazy init, version={VERSION})")
    app.run(host="0.0.0.0", port=port, debug=False)
