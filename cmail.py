import smtplib
from email.message import EmailMessage
def sendmail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('20jr1a05g3@gmail.com','qoef rkno wzzc zrhn')
    msg=EmailMessage()
    msg['From']='20jr1a05g3@gmail.com'
    msg['Subject']=subject
    msg['To']=to
    msg.set_content(body)
    server.send_message(msg)
    server.quit()


