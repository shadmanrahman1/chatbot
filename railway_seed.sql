-- Railway MySQL Database Setup Script
-- Run this in Railway MySQL Console

-- Create courses table
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
);

-- Create faqs table
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
);

-- Insert courses
INSERT INTO courses (title, description, price, duration, instructor, is_active) VALUES
('Python Programming Fundamentals', 'Learn Python from scratch. Covers variables, data types, loops, functions, and object-oriented programming. Perfect for beginners wanting to start their coding journey.', 299.99, 8, 'John Smith', TRUE),
('Java Development Bootcamp', 'Comprehensive Java course covering OOP, Spring Framework, and enterprise development. Build real-world applications and learn industry best practices.', 399.99, 12, 'Sarah Johnson', TRUE),
('Web Development with React', 'Master modern web development using React.js, HTML5, CSS3, and JavaScript. Build responsive websites and single-page applications.', 349.99, 10, 'Mike Davis', TRUE),
('Data Science with Python', 'Learn data analysis, machine learning, and visualization using Python, Pandas, NumPy, and Scikit-learn. Perfect for aspiring data scientists.', 449.99, 14, 'Dr. Emily Chen', TRUE),
('Mobile App Development', 'Create mobile apps for iOS and Android using React Native. Learn app deployment, UI/UX design, and mobile-specific development patterns.', 379.99, 12, 'Alex Rodriguez', TRUE);

-- Insert FAQs
INSERT INTO faqs (question, answer, keywords, course_id, is_active) VALUES
('What programming courses do you offer?', 'We offer Python Programming, Java Development, Web Development with React, Data Science with Python, and Mobile App Development. All courses are designed for practical, hands-on learning.', 'courses, programming, languages, available', NULL, TRUE),
('What are your office hours?', 'Our support team is available Monday to Friday, 9 AM to 6 PM (GMT+6). You can also reach us via WhatsApp anytime for quick questions!', 'office hours, support, contact, time', NULL, TRUE),
('How do I enroll in a course?', 'Enrollment is easy! Just message us with the course you are interested in, and we will guide you through the process. You can pay online or through mobile banking.', 'enroll, enrollment, registration, signup', NULL, TRUE),
('Do you provide certificates?', 'Yes! All students receive a completion certificate after successfully finishing their course. Our certificates are industry-recognized and can boost your career prospects.', 'certificate, certification, completion, credentials', NULL, TRUE),
('What payment methods do you accept?', 'We accept online payments, mobile banking (bKash, Nagad, Rocket), and bank transfers. We also offer installment plans for courses over $300.', 'payment, money, cost, price, bkash, nagad', NULL, TRUE),
('How much does the Python course cost?', 'The Python Programming Fundamentals course costs $299.99. This includes 8 weeks of instruction, hands-on projects, and lifetime access to course materials.', 'python, price, cost, fee', 1, TRUE),
('Is Python course good for beginners?', 'Absolutely! Our Python course is designed specifically for beginners. No prior programming experience required. We start from the very basics and gradually build up to advanced concepts.', 'python, beginner, basic, start, new', 1, TRUE),
('What does the Java course include?', 'The Java Development Bootcamp covers Core Java, Object-Oriented Programming, Spring Framework, database connectivity, and enterprise development. Duration: 12 weeks. Price: $399.99.', 'java, includes, content, curriculum', 2, TRUE),
('Do I need to know HTML before taking React course?', 'Basic HTML/CSS knowledge is helpful but not required. Our Web Development course covers HTML5, CSS3, JavaScript fundamentals before diving into React.js.', 'react, web, html, css, prerequisites', 3, TRUE),
('Do you offer support after course completion?', 'Yes! We provide 6 months of post-course support including career guidance, project reviews, and technical assistance. Our community forum is also available 24/7.', 'support, help, after, completion, assistance', NULL, TRUE),
('Can I get a refund if I am not satisfied?', 'We offer a 7-day money-back guarantee. If you are not satisfied within the first week, we will provide a full refund, no questions asked.', 'refund, money back, satisfaction, guarantee', NULL, TRUE);

-- Verify data
SELECT COUNT(*) as course_count FROM courses;
SELECT COUNT(*) as faq_count FROM faqs;

SELECT 'Database seeded successfully!' as status;
