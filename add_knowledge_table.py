"""
Add knowledge_articles table to the database
"""
from sqlalchemy import create_engine, text
from app.config import settings

def add_knowledge_table():
    engine = create_engine(settings.database_url)
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS knowledge_articles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        category VARCHAR(100) NOT NULL,
        tags TEXT,
        image_url VARCHAR(255),
        author_id INT,
        views INT DEFAULT 0,
        is_published BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # Insert sample data
    insert_samples_sql = """
    INSERT INTO knowledge_articles (title, content, category, tags, views, is_published)
    VALUES 
        ('Identifying Common Coconut Pests', 
         'Coconut rhinoceros beetle, coconut scale insect, and coconut leaf beetle are among the most common pests affecting coconut plantations. Each has distinct characteristics and requires different management strategies. Regular monitoring and early detection are key to effective pest management.',
         'pest-management',
         '["pest-identification", "coconut", "common-pests"]',
         245,
         TRUE),
        ('Integrated Pest Management (IPM) Strategy',
         'IPM combines biological, cultural, and chemical control methods to manage pests sustainably. Start with preventive measures, monitor regularly, and use chemical controls as a last resort. This holistic approach reduces environmental impact while maintaining crop health.',
         'best-practices',
         '["ipm", "sustainable", "best-practices"]',
         189,
         TRUE),
        ('Coconut Leaf Beetle Management',
         'Coconut leaf beetles damage leaves, reducing photosynthesis and overall tree health. Implement cultural practices like removing affected leaves and maintaining good sanitation. Use approved pesticides when infestations are severe, following all safety guidelines.',
         'pest-management',
         '["leaf-beetle", "management", "treatment"]',
         156,
         TRUE),
        ('Proper Fertilization Techniques',
         'Coconut trees require balanced nutrition for optimal growth and production. Apply fertilizers based on soil test results. Key nutrients include nitrogen, phosphorus, potassium, and micronutrients. Time applications to coincide with rainfall or irrigation for best absorption.',
         'fertilization',
         '["fertilizer", "nutrition", "soil-health"]',
         203,
         TRUE),
        ('Disease Prevention and Control',
         'Common coconut diseases include bud rot, stem bleeding, and leaf blight. Prevention through good cultural practices is essential. Ensure proper drainage, avoid injuries to trees, and remove infected plant material. Early detection allows for more effective treatment.',
         'disease-control',
         '["disease", "prevention", "treatment"]',
         178,
         TRUE)
    ON DUPLICATE KEY UPDATE title=title;
    """
    
    try:
        with engine.connect() as conn:
            # Create table
            print("Creating knowledge_articles table...")
            conn.execute(text(create_table_sql))
            conn.commit()
            print("✓ Table created successfully")
            
            # Insert sample data
            print("Inserting sample articles...")
            conn.execute(text(insert_samples_sql))
            conn.commit()
            print("✓ Sample articles inserted successfully")
            
            # Verify
            result = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles"))
            count = result.scalar()
            print(f"✓ Total articles in database: {count}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    add_knowledge_table()
