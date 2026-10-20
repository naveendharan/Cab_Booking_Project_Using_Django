# 🚖 RideGo – Cab Booking System

## 📌 Project Overview

RideGo is a web-based Cab Booking System developed using Python, Django, MySQL, HTML, CSS, and JavaScript. The application aims to simplify ride booking and provide an administrative dashboard for managing bookings, customer details, and fare settings.

## ✨ Features

- **User Authentication:** User registration and login.
- **Cab Booking:** Interface for entering ride details and managing bookings.
- **Admin Dashboard:** Centralized management of customer and booking information.
- **Dynamic Fare Management:** Admin can update the base fare and price per kilometre.
- **Fare Calculation:** Calculate ride fares based on distance and configured pricing.
- **Database Integration:** Store and manage application data using MySQL.
- **Responsive UI:** User-friendly interface built with HTML, CSS, and JavaScript.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Web application framework |
| MySQL | Relational database |
| HTML5 | Page structure |
| CSS3 | Styling and layout |
| JavaScript | Frontend interactivity |
| Git & GitHub | Version control and source code hosting |

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/naveendharan/Cab_Booking_Project_Using_Django.git
```

### 2. Navigate to the Project Directory

```bash
cd Cab_Booking_Project_Using_Django
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 4. Install Dependencies

If a `requirements.txt` file exists:

```bash
pip install -r requirements.txt
```

Otherwise, install Django and the MySQL driver required by your project:

```bash
pip install django mysqlclient
```

*The required database driver depends on your Django database configuration.*

### 5. Configure the Database

- Create a MySQL database for the project.
- Update the database name, username, password, host, and port in `settings.py`.
- Ensure the MySQL server is running.

### 6. Apply Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create an Administrator Account

```bash
python manage.py createsuperuser
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Open the application at:

`http://127.0.0.1:8000/`

## 🗄️ Database

MySQL is used to store application data, including user information, ride bookings, and pricing settings, depending on the implemented models.

## 🎯 Project Objective

The objective of RideGo is to demonstrate full-stack web development skills, Django application development, database integration, authentication, CRUD operations, and administrative management.

## 👨‍💻 Developer

**Naveendharan**

GitHub: [naveendharan](https://github.com/naveendharan)

Repository: [Cab Booking Project Using Django](https://github.com/naveendharan/Cab_Booking_Project_Using_Django)

---

*Note: Update the feature list and setup instructions to match the functionality and dependencies actually implemented in your project.*
