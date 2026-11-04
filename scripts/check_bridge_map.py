import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=55011,
    user="switch_app",
    password="J0-Efw91U4XjcYhS8CfA0qdHaUzi8oSx",
    dbname="switch"
)
cur = conn.cursor()
cur.execute("SET app.tenant_id = '00000000-0000-0000-0000-000000000000';")

cur.execute("SELECT * FROM bridge_message_map ORDER BY created_at DESC LIMIT 5;")
for r in cur.fetchall():
    print(r)
