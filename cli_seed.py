import subprocess
import os


def run_mysql_command():
    """Try to run mysql command directly with Railway credentials"""

    # Railway connection details
    host = "roundhouse.proxy.rlwy.net"
    port = "58662"
    user = "root"
    password = "bOFivGQlgWqIqJsopJroXStxJzmjmiPI"
    database = "railway"

    # Read the SQL file
    sql_file = "railway_seed.sql"

    try:
        # Try using mysql command line if available
        cmd = [
            "mysql",
            f"-h{host}",
            f"-P{port}",
            f"-u{user}",
            f"-p{password}",
            database,
            "-e",
            f"source {sql_file}",
        ]

        print("🔧 Trying mysql command line...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ SQL executed successfully via mysql CLI!")
            return True
        else:
            print(f"❌ MySQL CLI failed: {result.stderr}")

    except FileNotFoundError:
        print("❌ mysql command not found on system")
    except Exception as e:
        print(f"❌ Error: {e}")

    return False


def run_with_mycli():
    """Try using mycli if available"""
    host = "roundhouse.proxy.rlwy.net"
    port = "58662"
    user = "root"
    password = "bOFivGQlgWqIqJsopJroXStxJzmjmiPI"
    database = "railway"

    try:
        cmd = [
            "mycli",
            f"-h{host}",
            f"-P{port}",
            f"-u{user}",
            f"-p{password}",
            database,
            "-e",
            "source railway_seed.sql",
        ]

        print("🔧 Trying mycli...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ SQL executed successfully via mycli!")
            return True
        else:
            print(f"❌ mycli failed: {result.stderr}")

    except FileNotFoundError:
        print("❌ mycli not found on system")
    except Exception as e:
        print(f"❌ Error: {e}")

    return False


if __name__ == "__main__":
    print("🚀 Attempting direct SQL execution...")

    if not os.path.exists("railway_seed.sql"):
        print("❌ railway_seed.sql file not found!")
        exit(1)

    success = run_mysql_command() or run_with_mycli()

    if not success:
        print("\n💡 Alternative options:")
        print("1. Install MySQL client: https://dev.mysql.com/downloads/mysql/")
        print("2. Use Postman to test the endpoints when Railway deploys")
        print("3. Wait for Railway deployment and use health endpoint seeding")
        print("4. Use Railway CLI if available")
