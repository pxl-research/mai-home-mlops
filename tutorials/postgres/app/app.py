
import psycopg
import os
import random

def main() -> None:
    """
    Connects to a PostgreSQL database, creates a table if it doesn't exist,
    and inserts a random math score for a randomly selected name.
    """
    host_name = os.getenv("POSTGRES_HOST")
    dbname = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    
    # 1. Establish connection using psycopg.connect()
    # Note: Psycopg 3 uses a slightly different connection string syntax.
    try:
        conn = psycopg.connect(
            host=host_name,
            dbname=dbname,
            user=user,
            password=password,
            port=5432
        )
    except psycopg.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return

    # 2. Use a 'with' statement for automatic transaction management
    # and to ensure the connection and cursor are closed properly.
    with conn.cursor() as cursor:
        random_mark = random.randint(1, 50)
        names = ["Ollie", "Milow", "Nio", "Snoopy"]
        selected_name = random.choice(names)

        print(f"Inserting: {selected_name}, {random_mark}")

        create_table_query = """
        create table if not exists math_score(
            name varchar(200),
            score integer
        )
        """
        cursor.execute(create_table_query)
        
        # 3. Psycopg 3 uses parameterized queries for safety and clarity.
        # It's a best practice to avoid f-strings for SQL queries to prevent SQL injection.
        insert_query = """
        insert into math_score (name, score) values (%s, %s)
        """
        cursor.execute(insert_query, (selected_name, random_mark))
        
    # The 'with conn.cursor()' block automatically commits the transaction on success,
    # and handles rollbacks on errors. So explicit conn.commit() is not needed inside.
    
    print("Data Inserted successfully!")
    
    # The 'with' statement also handles closing the connection and cursor.
    # No need for explicit cursor.close() or conn.close().

if __name__ == "__main__":
    main()