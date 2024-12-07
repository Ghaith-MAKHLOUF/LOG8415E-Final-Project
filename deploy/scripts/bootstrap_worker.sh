#!/bin/bash

# Setup
## Exit if an error occurs (Ex. Wrong Checksum)
set -e

## Setup environment
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
source ~/.venv/bin/activate

## Install MySQL
sudo apt-get install mysql-server -y
# Start MySQL service
sudo systemctl start mysql
# Enable MySQL to start on boot
sudo systemctl enable mysql
# Run the MySQL secure installation script (interactive by default)
sudo mysql_secure_installation <<EOF 
n
y
y
y
y
EOF

## Install Sakila Database
# Download the database
wget https://downloads.mysql.com/docs/sakila-db.zip
# Extract
sudo apt install unzip
unzip /home/ubuntu/sakila-db.zip
# Create the database structure
sudo mysql -u root -e "source /home/ubuntu/sakila-db/sakila-schema.sql"
# Populate the database
sudo mysql -u root -e "source /home/ubuntu/sakila-db/sakila-data.sql"
# Confirm
sudo mysql -u root -e "USE sakila; SHOW FULL TABLES; SELECT COUNT(*) FROM film; SELECT COUNT(*) FROM film_text;"

## sysbench verification
# Install sysbench
sudo apt-get install sysbench -y
# Prepare the DB for sysbench
sudo sysbench /usr/share/sysbench/oltp_read_only.lua --mysql-db=sakila --mysql-user="root" --mysql-password="" prepare
# Run sysbench
sudo sysbench /usr/share/sysbench/oltp_read_only.lua --mysql-db=sakila --mysql-user="root" --mysql-password="" run

## Make a new user to access SQL Server
sudo sed -i "s/^bind-address.*/bind-address = 0.0.0.0/" /etc/mysql/mysql.conf.d/mysqld.cnf;
sudo systemctl restart mysql;
sudo mysql -e "CREATE USER 'proxy_user'@'%' IDENTIFIED BY '';";
sudo mysql -e "GRANT SELECT, INSERT, UPDATE, DELETE ON sakila.* TO 'proxy_user'@'%';";
sudo mysql -e "FLUSH PRIVILEGES;";

