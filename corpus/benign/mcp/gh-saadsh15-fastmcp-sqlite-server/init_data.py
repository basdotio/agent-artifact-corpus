import hashlib
import random
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, Index, func, insert

#connect to sqlite database
engine = create_engine('sqlite:///arzonama.db')

metadata = MetaData()
users_table = Table(
    'user',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('full_name', String, nullable=False),
    Column('email', String, nullable=False),
    Column('password', String(255), nullable=False),
    Column('created_at', DateTime, server_default=func.now()),
    Column('is_premium', Boolean, nullable=False, default=False)
)
Index('ix_user_email', users_table.c.email)

# Create table and index if they don't exist
metadata.create_all(engine, checkfirst=True)

#Sample data pools
first_names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy"]
last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
domains = ["example.com", "test.com", "sample.org", "demo.net", "mail.com", "web.org", "site.net", "email.com", "domain.org", "service.net"]

user_records = []
used_emails = set()  # To track used emails and ensure uniqueness

for i in range(50000):
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    full_name = f"{first_name} {last_name}"
    email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"
    # Ensure email uniqueness
    while email in used_emails:
        email = f"{first_name.lower()}.{last_name.lower()}_{random.randint(1, 999)}@{random.choice(domains)}"
    used_emails.add(email)
    mock_hash = hashlib.sha256(f"password{i}".encode()).hexdigest()  # Hash the password
    user_records.append({
        "full_name": full_name,
        "email": email,
        "password": mock_hash
    })
    
with engine.begin() as connection:
    connection.execute(insert(users_table), user_records)
    
print("Successfully inserted user records into the users table.")