

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid
import mimetypes

class ProjectAlert:
    def __init__(self, **kwargs):
        self.tracker = {"total_emails_sent": 0, "last_sent": None}
        self.total_emails_per_minute = 1 ## in case there are too many notifications
        self.email_user = kwargs['email_user']
        self.smtp_pass = kwargs['smtp_password']
        self.to_user = kwargs['notify_user']

    def check_availability(self):
        """
            Check availability is to check if we are sending within the limits, so we are not over notifying.
        """
        if(self.tracker['last_sent'] == None):
            return True
        else:
            last_sent = datetime.strptime(self.tracker['last_sent'],'%Y-%m-%d %H:%M:%S')
            
            mins_elapsed = (datetime.now() - last_sent).total_seconds() /60
            if(mins_elapsed>self.total_emails_per_minute):
                return True
            else:
                return False
        

    def update_tracker(self):
        curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.tracker["total_emails_sent"] += 1
        self.tracker["last_sent"] = curr_time

    def send_email(self, subject, message, image_file=None):
        if(not self.check_availability()):
            print("Limit Exceeded!")
            return
        self.update_tracker()
        print("Sending Notification...", end="")
        try:
            msg = EmailMessage()

            # generic email headers
            msg['Subject'] = f"ALERT: {subject}"
            msg['From'] = self.email_user
            msg['To'] = self.to_user
            msg['Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # set the plain text body
            msg.set_content("Email Notification from Camera Surveillance System")

            # now create a Content-ID for the image
            image_cid = make_msgid(domain='kozydfs.com')
            # if `domain` argument isn't provided, it will 
            # use your computer's name

            # set an alternative html body
            html = ""
            for msg in message:
                html += msg + "<br>"


            msg.add_alternative("""\
            <html>
                <body>
                    <p><B>ALERT</b>: {subject} <br>
                    {html}
                    </p>
                    <img src="cid:{image_cid}">
                </body>
            </html>
            """.format(image_cid=image_cid[1:-1],html=html, subject=subject),subtype='html')
            # image_cid looks like <long.random.number@xyz.com>
            # to use it as the img src, we don't need `<` or `>`
            # so we use [1:-1] to strip them off


            # now open the image and attach it to the email
            if(image_file):
                with open(image_file, 'rb') as img:

                    # know the Content-Type of the image
                    maintype, subtype = mimetypes.guess_type(img.name)[0].split('/')

                    # attach it
                    msg.get_payload()[1].add_related(img.read(), 
                                                        maintype=maintype, 
                                                        subtype=subtype, 
                                                        cid=image_cid)

                # Credentials
                username = self.email_user
                password =  self.smtp_pass

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
            print("Send Notification Failed!")
            print(e)
            

        # the message is ready now
        # you can write it to a file
        # or send it using smtplib


    def send_email1(self, subject, message, image_file=None):
        if(not self.check_availability()):
            print("Limit Exceeded!")
            return
        self.update_tracker()
        print("Sending Notification...", end="")
        try:
            from_address = self.email_user
            to_address = self.to_user
            

    ##https://mailmeteor.com/blog/gmail-smtp-settings



            # Create message container - the correct MIME type is multipart/alternative.
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Alert: {subject}"
            msg['From'] = self.email_user
            msg['To'] = self.to_user
            msg['Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Create the message (HTML).
            html = f"Alert: {subject}<P>"
            for msg in message:
                html += msg + "<br>"

            # Record the MIME type - text/html.
            part1 = MIMEText(html, 'html')

            # Attach parts into message container
            msg.attach(part1)

            # Credentials
            username = self.email_user
            password =  self.smtp_pass

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

