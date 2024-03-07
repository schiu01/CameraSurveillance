

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid
import mimetypes
import logging
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
            logging.warn("[Notification] Limited Exceeded for 1 Per minute.")
            return
        self.update_tracker()
        logging.info("Sending Notification...")
        print("Sending Notification...", end="")
        try:
            msg = EmailMessage()
            from_address = self.email_user
            to_address = self.to_user

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

            ## image_file has similar naming convention to the corresponding mp4 file
            mp4_file = image_file.split("/")[-1]
            mp4_file = mp4_file.replace("img_","raw_capture_").replace(".jpg",".mp4")
            

            # set an alternative html body
            html = f"<table><tr><th>ALERT: {subject}</th></tr>"
            for i, m1 in enumerate(message):
                html += f"<tr><td>{m1}</td></tr>"
            html += "</table>"


            msg.add_alternative("""\
            <html>
                <body>
                    
                    {html}
                    </p>
                    <img src="cid:{image_cid}">
                    <P>
                    <a href="http://192.168.1.23/surveillance/playvideo?file={video_file}">{video_file}</A> 
                    </P>
                </body>
            </html>
            """.format(image_cid=image_cid[1:-1],html=html, subject=subject, video_file=mp4_file),subtype='html')
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
            logging.error("Send Notification Failed!")
            logging.error(str(e))
            
