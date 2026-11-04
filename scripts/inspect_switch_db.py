import psycopg2
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(
    host="localhost",
    port=55011,
    user="switch_app",
    password="J0-Efw91U4XjcYhS8CfA0qdHaUzi8oSx",
    dbname="switch"
)
cur = conn.cursor()
cur.execute("SET app.tenant_id = '00000000-0000-0000-0000-000000000000';")

cur.execute("""
    SELECT seq, sender_id, sender_name, event_type, body, sent_at 
    FROM messages 
    WHERE room_id = 'b58680a3-370e-468b-abf7-1e66a813599f' 
    ORDER BY seq DESC LIMIT 20;
""")
rows = cur.fetchall()
print(f"Total messages in Telegram room: {len(rows)}")
for r in reversed(rows):
    print(f"[{r[0]}] {r[5]} | {r[2]} ({r[1]}): {r[4]}")
