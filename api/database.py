import os
import psycopg2
import psycopg2.extras

PG_DSN = os.environ["POSTGRES_DSN"]


def pg():
    return psycopg2.connect(PG_DSN, cursor_factory=psycopg2.extras.RealDictCursor)
