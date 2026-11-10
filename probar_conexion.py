import psycopg

from config.database import obtener_conexion


def probar_conexion():
    try:
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT current_database();")
                print("Conexión exitosa")
                print("Base de datos:", cursor.fetchone()[0])

                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)

                tablas = cursor.fetchall()
                print(f"Tablas encontradas: {len(tablas)}")

                for (nombre,) in tablas:
                    print("-", nombre)

    except (psycopg.Error, ValueError) as error:
        print("No se pudo completar la prueba:", error)


if __name__ == "__main__":
    probar_conexion()