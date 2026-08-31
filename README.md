# Clinical Dashboard - Novartis 2025

A Streamlit-based clinical data visualization and analysis dashboard for pharmaceutical research and clinical trial monitoring.

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [Development Workflow](#development-workflow)
- [Git Operations](#git-operations)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Prerequisites

Before you begin, ensure you have the following installed:

### **Required Software:**
- **Python 3.8 or higher** - [Download Python](https://www.python.org/downloads/)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **pip** (Python package manager) - Comes with Python 3.4+

### **Verify Installation:**

#### **Linux/Mac:**
```bash
python3 --version
git --version
pip --version
```

#### **Windows:**
```cmd
python --version
git --version
pip --version
```

## 📥 Installation & Setup

Follow these steps to set up the project on your local machine.

### **Step 1: Clone the Repository**

#### **Linux/Mac:**
```bash
# Clone the repository from GitHub
git clone https://github.com/Ananya-m0140/novartis-25.git

# Navigate to the project directory
cd novartis-25/clinial-dashboard
```

#### **Windows (Command Prompt/PowerShell):**
```cmd
# Clone the repository from GitHub
git clone https://github.com/Ananya-m0140/novartis-25.git

# Navigate to the project directory
cd novartis-25\clinial-dashboard
```

### **Step 2: Create Virtual Environment**

A virtual environment isolates project dependencies from your system Python.

#### **Linux/Mac:**
```bash
# Create a virtual environment named 'venv'
python3 -m venv venv
```

#### **Windows:**
```cmd
# Create a virtual environment named 'venv'
python -m venv venv
```

### **Step 3: Activate Virtual Environment**

#### **Linux/Mac:**
```bash
# Activate the virtual environment
source venv/bin/activate

# Verify activation (you should see '(venv)' in your prompt)
(venv) $
```

#### **Windows (Command Prompt):**
```cmd
# Activate the virtual environment
venv\Scripts\activate.bat

# Verify activation (you should see '(venv)' in your prompt)
(venv) C:\path\to\project>
```

#### **Windows (PowerShell):**
```powershell
# Activate the virtual environment
venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activating again
```

### **Step 4: Install Dependencies**

#### **Both Linux/Mac & Windows:**
```bash
# Install all required packages from requirements.txt
pip install -r requirements.txt

# If requirements.txt doesn't exist or is empty, install common packages:
pip install streamlit pandas numpy plotly matplotlib seaborn
```

**Expected Output:**
```
Collecting streamlit
  Downloading streamlit-1.28.0-py3-none-any.whl (8.4 MB)
Collecting pandas
  Downloading pandas-2.1.3-cp311-cp311-win_amd64.whl (11.0 MB)
...
Successfully installed streamlit-1.28.0 pandas-2.1.3 ...
```

## 🏃 Running the Application

### **Step 5: Launch the Streamlit Dashboard**

#### **Linux/Mac:**
```bash
# Basic run (default port 8501)
streamlit run app.py

# Or with specific configuration
streamlit run app.py --server.port 8501 --server.headless false
```

#### **Windows:**
```cmd
# Basic run (default port 8501)
streamlit run app.py

# Or with specific configuration
streamlit run app.py --server.port 8501 --server.headless false
```

### **Step 6: Access the Dashboard**

1. The terminal will display:
   ```
   You can now view your Streamlit app in your browser.
   
   Local URL: http://localhost:8501
   Network URL: http://192.168.x.x:8501
   ```

2. **Automatic Opening**: The dashboard should open automatically in your default browser

3. **Manual Access**: If it doesn't open automatically:
   - Open your web browser
   - Navigate to: `http://localhost:8501`
   - For network access: Use the Network URL shown in terminal

## 🛠 Development Workflow

### **Working with the Virtual Environment**

#### **Check if Virtual Environment is Active:**
```bash
# Linux/Mac/Windows (when active shows path containing 'venv')
which python
# or
where python  # Windows

# Should show something like:
# /path/to/project/venv/bin/python (Linux/Mac)
# C:\path\to\project\venv\Scripts\python.exe (Windows)
```

#### **Deactivate Virtual Environment:**
```bash
# Both Linux/Mac & Windows
deactivate

# Your prompt should no longer show '(venv)'
```

### **Updating Requirements File**

When you add new Python packages to the project:

#### **Both Linux/Mac & Windows:**
```bash
# 1. Make sure virtual environment is active
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 2. Install new package
pip install <package-name>

# 3. Update requirements.txt with all current packages
pip freeze > requirements.txt

# 4. Verify the update
cat requirements.txt  # Linux/Mac
# or
type requirements.txt  # Windows
```

### **Starting Fresh (Delete and Recreate Virtual Environment)**

#### **Linux/Mac:**
```bash
# 1. Deactivate if active
deactivate

# 2. Delete the virtual environment
rm -rf venv

# 3. Create new virtual environment
python3 -m venv venv

# 4. Activate and install requirements
source venv/bin/activate
pip install -r requirements.txt
```

#### **Windows:**
```cmd
# 1. Deactivate if active
deactivate

# 2. Delete the virtual environment
rmdir /s venv

# 3. Create new virtual environment
python -m venv venv

# 4. Activate and install requirements
venv\Scripts\activate
pip install -r requirements.txt
```

## 🔄 Git Operations

### **Making and Saving Changes**

#### **Step 1: Check Current Status**
```bash
# See what files have changed
git status
```

#### **Step 2: Stage Changes**
```bash
# Add specific files
git add app.py
git add requirements.txt

# Or add all changes
git add .
```

#### **Step 3: Commit Changes**
```bash
# Commit with a descriptive message
git commit -m "Updated dashboard layout and added new visualizations"

# For detailed commit message:
git commit -m "Subject: Update dashboard

- Added patient demographics section
- Fixed data loading bug
- Updated color scheme for better accessibility"
```

#### **Step 4: Push to GitHub**
```bash
# Push to main branch
git push origin main

# If using a different branch
git push origin feature/new-visualization
```

### **Working with Branches**

#### **Create a New Branch:**
```bash
git checkout -b feature/new-feature
```

#### **Switch Between Branches:**
```bash
git checkout main
git checkout feature/new-feature
```

#### **Update Local Repository:**
```bash
# Pull latest changes from GitHub
git pull origin main

# If you have local changes, stash them first
git stash
git pull origin main
git stash pop
```

## 📁 Project Structure

```
novartis-25/
├── clinial-dashboard/
│   ├── app.py                 # Main Streamlit application
│   ├── requirements.txt       # Python dependencies
│   ├── .gitignore            # Files to ignore in git
│   ├── README.md             # This documentation file
│   ├── data/                 # Data directory
│   │   ├── clinical_trials.csv
│   │   ├── patient_data.json
│   │   └── processed/
│   ├── utils/                # Utility functions
│   │   ├── data_loader.py
│   │   ├── visualization.py
│   │   └── calculations.py
│   ├── pages/                # Multi-page app sections
│   │   ├── 01_📊_Overview.py
│   │   ├── 02_👥_Patients.py
│   │   └── 03_📈_Analytics.py
│   └── assets/               # Static assets
│       ├── images/
│       ├── styles.css
│       └── favicon.ico
├── .github/                  # GitHub workflows
└── docs/                    # Documentation
```

### **File Descriptions:**
- **`app.py`**: Entry point of the Streamlit application
- **`requirements.txt`**: Lists all Python package dependencies
- **`.gitignore`**: Specifies files to exclude from version control
- **`data/`**: Contains all data files (CSV, JSON, etc.)
- **`utils/`**: Helper functions for data processing and visualization
- **`pages/`**: Additional pages for multi-page Streamlit apps

## 🐛 Troubleshooting

### **Common Issues and Solutions:**

#### **1. "Command not found: streamlit"**
```bash
# Solution: Reinstall streamlit in activated venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

pip install --upgrade streamlit
```

#### **2. Port 8501 Already in Use**
```bash
# Solution 1: Kill the process using port 8501
# Linux/Mac:
sudo lsof -ti:8501 | xargs kill -9

# Windows:
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Solution 2: Use a different port
streamlit run app.py --server.port 8502
```

#### **3. Virtual Environment Activation Fails (Windows)**
```powershell
# If you get "execution policy" error in PowerShell:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# If scripts are disabled, run Command Prompt as administrator
```

#### **4. Module Import Errors**
```bash
# Make sure you're in the project directory
pwd  # Should show .../clinial-dashboard

# Install missing package
pip install <missing-package-name>

# Update requirements.txt
pip freeze > requirements.txt
```

#### **5. Git Authentication Issues**
```bash
# If asked for username/password repeatedly:
# Solution 1: Use SSH instead of HTTPS
git remote set-url origin git@github.com:Ananya-m0140/novartis-25.git

# Solution 2: Use personal access token
# Generate token at: https://github.com/settings/tokens
# Use token as password when prompted
```

### **Debug Commands:**

```bash
# Check Python version and location
python --version
which python

# Check installed packages
pip list

# Check Streamlit version
streamlit --version

# Test basic Streamlit functionality
streamlit hello
```

## 🔧 Advanced Configuration

### **Custom Streamlit Configuration:**

Create `.streamlit/config.toml`:
```toml
[server]
port = 8501
address = "0.0.0.0"
headless = false

[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### **Environment Variables:**

Create `.env` file (add to `.gitignore`):
```env
DATABASE_URL=postgresql://user:password@localhost:5432/clinical_db
API_KEY=your_api_key_here
DEBUG_MODE=False
```

Load in `app.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv("DATABASE_URL")
```

## 📊 Performance Tips

1. **Cache Expensive Operations:**
```python
@st.cache_data
def load_data(filepath):
    return pd.read_csv(filepath)
```

2. **Use Session State for User Data:**
```python
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}
```

3. **Optimize Data Loading:**
- Use Parquet format for large datasets
- Implement pagination for large tables
- Use progressive loading

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes and commit:**
   ```bash
   git commit -m "Add amazing feature"
   ```
4. **Push to your branch:**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### **Commit Message Guidelines:**
- Use present tense ("Add feature" not "Added feature")
- Start with capital letter
- Reference issues with #issue_number

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **GitHub Issues**: [Report a Bug](https://github.com/Ananya-m0140/novartis-25/issues)
- **Email**: [your-email@example.com]
- **Documentation**: [Link to detailed docs if available]

## 🎉 Acknowledgments

- Novartis for the opportunity
- Streamlit team for the amazing framework
- Open source community for libraries and tools

---

**Made with ❤️ by Ananya Mondal | 23CS10002**

*Last Updated: January 2025*
```

This comprehensive README includes:
1. **Complete installation instructions** for both operating systems
2. **Step-by-step workflow** from cloning to deployment
3. **Troubleshooting guide** for common issues
4. **Project structure** documentation
5. **Git operations** for version control
6. **Development best practices**
7. **Performance optimization tips**
8. **Contribution guidelines**

Save this as `README.md` in your project root directory. It provides everything needed for users (and yourself) to work with the project effectively.
