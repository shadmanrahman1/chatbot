"""
Database seed script for Railway MySQL
Populates the database with EdTech courses and FAQs
"""

import os
import mysql.connector
from urllib.parse import urlparse
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_db_config():
    """Build database configuration from environment variables"""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            parsed = urlparse(database_url)
            return {
                "host": parsed.hostname,
                "port": parsed.port or 3306,
                "user": parsed.username,
                "password": parsed.password,
                "database": parsed.path.lstrip("/"),
            }
        except Exception as e:
            logger.error(f"Failed to parse DATABASE_URL: {e}")

    # Fallback to individual environment variables
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "edtech_bot"),
    }


def create_tables(cursor):
    """Create necessary tables if they don't exist"""

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

    logger.info("✅ Tables created successfully")


def seed_courses(cursor):
    """Insert sample courses"""

    # Clear existing courses
    cursor.execute("DELETE FROM courses")

    courses = [
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
        courses,
    )

    logger.info(f"✅ Inserted {len(courses)} courses")


def seed_faqs(cursor):
    """Insert sample FAQs"""

    # Clear existing FAQs
    cursor.execute("DELETE FROM faqs")

    faqs = [
        # General FAQs
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
            "Enrollment is easy! Just message us with the course you're interested in, and we'll guide you through the process. You can pay online or through mobile banking.",
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
            "Can I get a refund if I'm not satisfied?",
            "We offer a 7-day money-back guarantee. If you're not satisfied within the first week, we'll provide a full refund, no questions asked.",
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
        faqs,
    )

    logger.info(f"✅ Inserted {len(faqs)} FAQs")


def seed_database():
    """Main seeding function"""
    try:
        # Get database configuration
        db_config = build_db_config()
        logger.info(
            f"🔗 Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['database']}"
        )

        # Connect to database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        logger.info("✅ Database connection successful")

        # Create tables
        create_tables(cursor)

        # Seed data
        seed_courses(cursor)
        seed_faqs(cursor)

        # Commit changes
        connection.commit()

        # Verify data
        cursor.execute("SELECT COUNT(*) FROM courses")
        course_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM faqs")
        faq_count = cursor.fetchone()[0]

        logger.info(f"🎉 Database seeding completed successfully!")
        logger.info(f"📚 Total courses: {course_count}")
        logger.info(f"❓ Total FAQs: {faq_count}")

    except mysql.connector.Error as e:
        logger.error(f"❌ Database error: {e}")
        if connection:
            connection.rollback()
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if connection:
            connection.rollback()
    finally:
        if "cursor" in locals():
            cursor.close()
        if "connection" in locals() and connection.is_connected():
            connection.close()
            logger.info("🔒 Database connection closed")


if __name__ == "__main__":
    logger.info("🌱 Starting database seeding...")
    seed_database()
