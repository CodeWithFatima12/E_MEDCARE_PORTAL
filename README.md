

# AI-Powered E-Medcare Portal

The **AI-Powered E-Medcare Portal** is a centralized healthcare management system designed to connect patients, doctors, and pharmacists through a unified digital platform[cite: 1]. Developed as a Final Year Project at the **University of the Punjab**, the system emphasizes proactive health monitoring through artificial intelligence[cite: 1].

## Key Features

*   **My Health Pro (AI Module)**: Predicts potential health risks and chronic conditions using machine learning models trained on patient vitals[cite: 1].
*   **Virtual Consultations**: Integrated video calling capabilities for remote patient-doctor interactions.
*   **Integrated Pharmacy**: A digital storefront for ordering medications with built-in cart functionality.
*   **Smart Scheduling**: Real-time appointment booking and management for clinical staff[cite: 1].
*   **Secure Dashboards**: Role-specific interfaces ensuring data privacy and streamlined workflows for all users.
* **Smart Customized Diet Planner**: An intelligent module that generates personalized meal plans based on a user's health data, dietary restrictions, and specific wellness goals, often powered by the Gemini API.
* **Lab Test Booking**: A dedicated  module for online lab test booking.
## Tech Stack

*   **Language**: Python 3.11+ (Note: Stability issues may occur on pre-release versions like 3.14).
*   **Framework**: Django 5.0.
*   **Database**: MySQL 8.0.
*   **Libraries**: Scikit-learn, Pandas, NumPy, MySQLclient.
*   **Machine Learning Algorithum**:Random Forest Classifier.
*   **Frontend**: HTML5, CSS3, JavaScript (AJAX for pharmacy interactions).  
*   **Containerization**: Docker & Docker Compose (Local Environment).

---  

##  Local Installation & Setup

Follow these steps to set up the development environment on your local machine.

### 1. Prerequisites
*   Python 3.11 or 3.12 installed.
*   MySQL Server 8.0 installed and running.

### 2. Clone the Repository
```bash
git clone https://github.com/CodeWithFatima12/E_MEDCARE_PORTAL.git
cd E_MEDCARE_PORTAL
```

### 3. Set Up Virtual Environment
Creating a virtual environment ensures that project dependencies do not interfere with your global Python installation.
```powershell
# Create the environment
python -m venv venv

# Activate the environment
.\venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Database & Environment
Create a `.env` file in the root directory (`E_MEDCARE_PORTAL/`) and add your local MySQL details:
```env
DB_NAME=e_medcare_db
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

SECRET_KEY=your_secret_key_here
```

### 6. Initialize the Database
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Run the Application
```bash
python manage.py runserver
```
*The portal will be accessible at `[http://127.0.0.1:8000/](http://127.0.0.1:8000/)`.*

---

##  Project Structure

*   **`accounts/`**: Logic for user authentication and Role-Based Access Control.
*   **`ai_module/`**: Predictive health models and data processing scripts.
*   **`pharmacy/`**: Product management and e-commerce logic.
*   **`appointment/`**: Scheduling system and video conferencing integration.
*   **`Lab/`**: For Online Lab Test Bookings.

##  Contributors

*   **Fatima Babar** (Project Lead, Appontment Module,Model Training)
*   **Shifa Zahid** (Lab Module,QA)
*   **Shifa Naseer** (Pharmacy Module,AI Module,DataBase Designer)
*   **Azka Hafeez** (Authentication,Frontend)

---

##  Acknowledgment
We would like to express our deepest gratitude to our project advisor, Dr. Saad Khan, for his invaluable guidance, technical insights, and constant encouragement throughout the development of the AI-Powered E-Medcare Portal.  
 We are truly grateful for the time he invested in mentoring our team and for helping us bridge the gap between academic theory and real-world application.






