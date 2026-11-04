import psycopg2
import json

conn = psycopg2.connect(host='localhost', port=55011, user='switch_app', password='J0-Efw91U4XjcYhS8CfA0qdHaUzi8oSx', dbname='switch')
cur = conn.cursor()
cur.execute("SET app.tenant_id = '00000000-0000-0000-0000-000000000000';")
cur.execute("SELECT seq, sender_id, event_type, body, content FROM messages WHERE seq IN (153, 154);")
for r in cur.fetchall():
    print(f"[{r[0]}] sender={r[1]}, event_type={r[2]}, body={r[3]}")
    print("content:", json.dumps(r[4], indent=2, default=str))

