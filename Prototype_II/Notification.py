

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

class ProjectAlert:
    def __init__(self):
        self.tracker = {"total_emails_sent": 0, "last_sent": None}
        self.total_emails_per_minute = 1 ## in case there are too many notifications

    def check_availability(self):
        """
            Check availability is to check if we are sending within the limits, so we are not over notifying.
        """
        if(self.tracker['last_sent'] == None):
            return True
        else:
            last_sent = datetime.strptime(self.tracker['last_sent'],'%Y-%m-%d %H:%M:%S')
            mins_elapsed = (datetime.now() - last_sent).min
            if(mins_elapsed>self.total_emails_per_minute):
                return True
            else:
                return False
        

    def update_tracker(self):
        curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.tracker["total_emails_sent"] += 1
        self.tracker["last_sent"] = curr_time

    def send_email(self, subject, message):
        if(not self.check_availability()):
            return
        self.update_tracker()
        print("Sending Notification...", end="")
        try:
            from_address = "schiu01@gmail.com"
            to_address = "schiu73@gmail.com"
            

    ##https://mailmeteor.com/blog/gmail-smtp-settings



            # Create message container - the correct MIME type is multipart/alternative.
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Alert: {subject}"
            msg['From'] = from_address
            msg['To'] = to_address
            msg['Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Create the message (HTML).
            html = f"""\
                Alert: {subject}

                Message: {message}
            """

            # Record the MIME type - text/html.
            part1 = MIMEText(html, 'html')

            # Attach parts into message container
            msg.attach(part1)

            # Credentials
            username = 'schiu01@gmail.com'
            

            # Sending the email
            ## note - this smtp config worked for me, I found it googling around, you may have to tweak the # (587) to get yours to work
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            server.login(username,password)
            server.sendmail(from_address, to_address, msg.as_string())
            server.quit()
            print("Done")
        except Exception as e:
            print("Failed")
            print(e)

