"""Project package.

PyMySQL is registered as MySQLdb so Windows XAMPP users do not have to compile
mysqlclient. The version tuple satisfies Django's client version check.
"""

try:
    import pymysql

    pymysql.version_info = (2, 2, 4, 'final', 0)
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
