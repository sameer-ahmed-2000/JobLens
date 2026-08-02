import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL or any(placeholder in DATABASE_URL for placeholder in ["<password>", "<your-aiven-host>", "<port>"]):
    print("Error: DATABASE_URL is not set or contains placeholder values in your environment/.env file.")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print('--- jobs columns ---')
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'jobs'")
for row in cur.fetchall():
    print(row)

print('--- vector extension ---')
cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
for row in cur.fetchall():
    print(row)

print('--- sample embeddings ---')
cur.execute("SELECT id, embedding IS NOT NULL as has_embedding FROM jobs LIMIT 5")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()