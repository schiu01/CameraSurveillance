import sys
sys.path.insert(0, '/opt/surveillance/www')
from myapp import app as application

if __name__ == "__main__":
	application.run()
