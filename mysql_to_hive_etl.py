__author__ = 'udaysharma'
# File Name: mysql_to_hive_etl.py
from pyspark import SparkContext, SparkConf
from pyspark.sql import SQLContext, HiveContext
from pyspark.sql import functions as sqlfunc

# Define database connection parameters
MYSQL_DRIVER_PATH = "/usr/local/spark/python/lib/mysql-connector-java-5.1.36-bin.jar"
MYSQL_USERNAME = '<USER_NAME >'
MYSQL_PASSWORD = '********'
MYSQL_CONNECTION_URL = "jdbc:mysql://localhost:3306/employees?user=" + MYSQL_USERNAME+"&password="+MYSQL_PASSWORD 

# Define Spark configuration
conf = SparkConf()
conf.setMaster("spark://Box.local:7077")
conf.setAppName("MySQL_import")
conf.set("spark.executor.memory", "1g")

# Initialize a SparkContext and SQLContext
sc = SparkContext(conf=conf)
sql_ctx = SQLContext(sc)

# Initialize hive context
hive_ctx = HiveContext(sc)

# Source 1 Type: MYSQL
# Schema Name  : EMPLOYEE
# Table Name   : EMPLOYEES
# + --------------------------------------- +
# | COLUMN NAME| DATA TYPE    | CONSTRAINTS |
# + --------------------------------------- +
# | EMP_NO     | INT          | PRIMARY KEY |
# | BIRTH_DATE | DATE         |             |
# | FIRST_NAME | VARCHAR(14)  |             |
# | LAST_NAME  | VARCHAR(16)  |             |
# | GENDER     | ENUM('M'/'F')|             |
# | HIRE_DATE  | DATE         |             |
# + --------------------------------------- +
df_employees = sql_ctx.load(
    source="jdbc",
    path=MYSQL_DRIVER_PATH,
    driver='com.mysql.jdbc.Driver',
    url=MYSQL_CONNECTION_URL,
    dbtable="employees")

# Source 2 Type : MYSQL
# Schema Name   : EMPLOYEE
# Table Name    : SALARIES
# + -------------------------------- +
# | COLUMN NAME | TYPE | CONSTRAINTS |
# + -------------------------------- +
# | EMP_NO      | INT  | PRIMARY KEY |
# | SALARY      | INT  |             |
# | FROM_DATE   | DATE | PRIMARY KEY |
# | TO_DATE     | DATE |             |
# + -------------------------------- +
df_salaries = sql_ctx.load(
    source="jdbc",
    path=MYSQL_DRIVER_PATH,
    driver='com.mysql.jdbc.Driver',
    url=MYSQL_CONNECTION_URL,
    dbtable="salaries")

# Perform INNER JOIN on  the two data frames on EMP_NO column
# As of Spark 1.4 you don't have to worry about duplicate column on join result
df_emp_sal_join = df_employees.join(df_salaries, "emp_no").select("emp_no", "birth_date", "first_name",
                                                             "last_name", "gender", "hire_date",
                                                             "salary", "from_date", "to_date")

# Adding a column 'year' to the data frame for partitioning the hive table
df_add_year = df_emp_sal_join.withColumn('year', F.year(df_emp_sal_join.to_date))

# Adding a load date column to the data frame
df_final = df_add_year.withColumn('Load_date', F.current_date())

df_final.repartition(10)

# Registering data frame as a temp table for SparkSQL
hive_ctx.registerDataFrameAsTable(df_final, "EMP_TEMP")

# Target Type: APACHE HIVE
# Database   : EMPLOYEES
# Table Name : EMPLOYEE_DIM
# + ------------------------------- +
# | COlUMN NAME| TYPE   | PARTITION |
# + ------------------------------- +
# | EMP_NO     | INT    |           |
# | BIRTH_DATE | DATE   |           |
# | FIRST_NAME | STRING |           |
# | LAST_NAME  | STRING |           |
# | GENDER     | STRING |           |
# | HIRE_DATE  | DATE   |           |
# | SALARY     | INT    |           |
# | FROM_DATE  | DATE   |           |
# | TO_DATE    | DATE   |           |
# | YEAR       | INT    | PRIMARY   |
# | LOAD_DATE  | DATE   | SUB       |
# + ------------------------------- +
# Storage Format: ORC

# Inserting data into the Target table
hive_ctx.sql("INSERT OVERWRITE TABLE EMPLOYEES.EMPLOYEE_DIM PARTITION (year, Load_date) \
            SELECT EMP_NO, BIRTH_DATE, FIRST_NAME, LAST_NAME, GENDER, HIRE_DATE, \
            SALARY, FROM_DATE, TO_DATE, year, Load_date FROM EMP_TEMP")