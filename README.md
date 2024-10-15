# NullLink-Pi
 
### Dependencies
- `sudo apt-get install curl`
- `pip install bleak`

### Setup

**AWS CLI**
1. `sudo apt install awscli`
2. `aws configure`

**Boto3 (AWS)**
1. Init: cd to project folder, `python3 -m venv myenv` 
2. Start session: `source myenv/bin/activate`
3. Init: `pip install boto3` (this will persist in myenv)
4. (Opt) run your script, eg, `python3 S3.py`
5. `deactivate`

**Running myenv in VS Code**
1. Ctrl + Shift + P; Python: Select Interpreter (select myenv)

**SQLite Browser**
1. `sudo apt update`
2. `sudo apt install sqlitebrowser`
3. `sqlitebrowser`
