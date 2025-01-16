Here’s a **README.md** file based on your instructions:

* * *

Askara Tender Search
====================

Overview
--------

Askara Tender Search is a Python-based web application to help you search for tenders from specific sources. Follow the steps below to set it up and run it on a Windows machine.

* * *

Prerequisites
-------------

*   Windows OS
*   Python version **3.10.11**

* * *

Installation Steps
------------------

### Step 1: Download and Install Python

1.  Download Python version **3.10.11** from the official website:  
    [Python 3.10.11 64\-bit Installer](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe)
2.  During the installation:
    *   **Select "Add Python to PATH"** before proceeding.
    *   Complete the installation process.

* * *

### Step 2: Download the Application

1.  Go to the GitHub repository:  
    [Askara Tender Search GitHub Repository](https://github.com/amanattar/askara_tender_search)
2.  Click the green **Code** button and select **Download ZIP**.
3.  Locate the downloaded ZIP file on your system and unzip it.

* * *

### Step 3: Install Dependencies

1.  Open the unzipped folder containing all the files.
2.  Click on the **path bar** at the top of the folder and type `cmd`. Press **Enter** to open the Command Prompt in the current directory.
3.  Run the following command to install the required dependencies:
    
    ```bash
    pip install -r requirements.txt 
    ```
    
4.  Wait for all the packages to be installed, then close the Command Prompt.

* * *

### Step 4: Run the Application

1.  Navigate to the folder containing the application files.
2.  Click the **path bar** again, type `cmd`, and press **Enter**.
3.  Start the application by running:
    
    ```bash
    python app.py
    ```
    
4.  The Command Prompt will show output similar to:
    
    ```vbnet
    * Serving Flask app 'app'
     * Debug mode: on
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
     * Running on http://127.0.0.1:5000
    Press CTRL+C to quit
     * Restarting with stat
     * Debugger is active!
     * Debugger PIN: 361-727-878
    ```
    

* * *

### Step 5: Access the Application

1.  Open your web browser.
2.  Type the following URL in the address bar and press **Enter**:
    
    ```arduino
    http://127.0.0.1:5000
    ```
    
3.  Follow the on-screen instructions to use the application as demonstrated in the video tutorial.

* * *

Notes
-----

*   This application is for development purposes and uses Flask's built-in development server. For production, consider using a WSGI server like Gunicorn.
*   Ensure you have an active internet connection to install dependencies and access external resources.

* * *

Let me know if you need further adjustments or additional details! 😊